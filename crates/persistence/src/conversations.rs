//! Project-bound local provider sessions and durable send intents; never credentials.
use super::*;
use serde_json::{Value, json};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conversation {
    pub id: String,
    pub project_id: String,
    pub title: String,
    pub created_at: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderExchange {
    pub id: String,
    pub project_id: String,
    pub session_id: String,
    pub packet_digest: String,
    pub user_draft: String,
    pub prompt: String,
    pub prompt_hash: String,
    pub ordinal: u64,
    pub status: String,
    pub response_text: Option<String>,
    pub error_code: Option<String>,
    pub accepted_review: bool,
    pub created_at: String,
}
impl ProviderExchange {
    pub fn sent_id(&self) -> String {
        format!("{}:user", self.id)
    }
    pub fn response_id(&self) -> String {
        format!("{}:assistant", self.id)
    }
}
fn exchange_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<ProviderExchange> {
    Ok(ProviderExchange {
        id: row.get(0)?,
        project_id: row.get(1)?,
        session_id: row.get(2)?,
        packet_digest: row.get(3)?,
        user_draft: row.get(4)?,
        prompt: row.get(5)?,
        prompt_hash: row.get(6)?,
        ordinal: row.get(7)?,
        status: row.get(8)?,
        response_text: row.get(9)?,
        error_code: row.get(10)?,
        accepted_review: row.get(11)?,
        created_at: row.get(12)?,
    })
}
impl Store {
    pub fn self_report(&self, project: &str, exchange: &str) -> Result<Option<Value>> {
        let row: Option<(String, String)> = self.connection.query_row(
            "SELECT status,report_json FROM provider_self_reports WHERE project_id=?1 AND exchange_id=?2",
            params![project,exchange], |r| Ok((r.get(0)?,r.get(1)?))).optional()?;
        row.map(|(status, body)| {
            let mut value: Value = serde_json::from_str(&body)?;
            value["status"] = json!(status);
            Ok(value)
        })
        .transpose()
    }
    pub fn prepare_self_report(&self, project: &str, exchange: &str, report: &Value) -> Result<()> {
        self.connection.execute(
            "INSERT INTO provider_self_reports VALUES(?1,?2,'prepared',?3) ON CONFLICT(exchange_id) DO UPDATE SET report_json=excluded.report_json WHERE provider_self_reports.project_id=excluded.project_id AND provider_self_reports.status='prepared'",
            params![exchange, project, serde_json::to_string(report)?],
        )?;
        Ok(())
    }
    pub fn claim_self_report(&self, project: &str, exchange: &str) -> Result<bool> {
        Ok(self.connection.execute("UPDATE provider_self_reports SET status='sending' WHERE project_id=?1 AND exchange_id=?2 AND status='prepared' AND EXISTS (SELECT 1 FROM projects p WHERE p.id=provider_self_reports.project_id AND p.status='active' AND p.state_version=json_extract(provider_self_reports.report_json,'$.state_version'))",
            params![project,exchange])? == 1)
    }
    pub fn finish_self_report(
        &self,
        project: &str,
        exchange: &str,
        status: &str,
        report: &Value,
        candidates: &[StateMutationCandidate],
        at: &str,
    ) -> Result<()> {
        let tx = self.connection.unchecked_transaction()?;
        for candidate in candidates {
            self.record_candidate(candidate, at)?;
        }
        self.connection.execute("UPDATE provider_self_reports SET status=?3,report_json=?4 WHERE project_id=?1 AND exchange_id=?2",
            params![project,exchange,status,serde_json::to_string(report)?])?;
        tx.commit()?;
        Ok(())
    }
    pub fn label_self_report(
        &self,
        project: &str,
        exchange: &str,
        candidate: &str,
        label: &str,
        at: &str,
    ) -> Result<Value> {
        if !matches!(label, "accurate" | "false_positive" | "unreviewed") {
            return Err(StoreError::Integrity("invalid precision label".into()));
        }
        let tx = self.connection.unchecked_transaction()?;
        let mut report = self
            .self_report(project, exchange)?
            .ok_or_else(|| StoreError::Integrity("self-report missing".into()))?;
        if report["status"] != "complete"
            || !report["candidates"]
                .as_array()
                .is_some_and(|rows| rows.iter().any(|r| r["candidate_id"] == candidate))
        {
            return Err(StoreError::Integrity(
                "candidate not in completed self-report".into(),
            ));
        }
        report["labels"][candidate] = json!(label);
        self.connection.execute("UPDATE provider_self_reports SET report_json=?3 WHERE project_id=?1 AND exchange_id=?2",
            params![project,exchange,serde_json::to_string(&report)?])?;
        self.audit(
            project,
            "SELF_REPORT_PRECISION_LABEL",
            exchange,
            &json!({"candidate_id":candidate,"label":label,"authority_changed":false}),
            at,
        )?;
        tx.commit()?;
        Ok(report)
    }
    pub fn create_conversation(
        &self,
        project: &str,
        id: &str,
        title: &str,
        at: &str,
    ) -> Result<Conversation> {
        let owner = self
            .project(project)?
            .ok_or_else(|| StoreError::ProjectNotFound(project.into()))?;
        if title.trim().is_empty() || title.chars().count() > 120 {
            return Err(StoreError::Integrity(
                "conversation title must be 1..120 characters".into(),
            ));
        }
        if owner.status != "active" {
            return Err(StoreError::Integrity("Project is archived".into()));
        }
        if let Some(existing) = self.conversation(project, id)? {
            return Ok(existing);
        }
        let transaction = self.connection.unchecked_transaction()?;
        transaction.execute("INSERT INTO provider_sessions(id,project_id,workstream_id,provider,conversation_key_hash,adapter_version,fork_state_version,attached_at) VALUES(?1,?2,?3,'tom-assist/openai-oauth',?4,'oauth-broker/1',?5,?6)", params![id,project,format!("chat:{id}"),canonical_sha256(&id)?,owner.state_version,at])?;
        transaction.execute(
            "INSERT INTO chat_conversations VALUES(?1,?2,?3,?4)",
            params![id, project, title, at],
        )?;
        transaction.commit()?;
        self.conversation(project, id)?
            .ok_or_else(|| StoreError::Integrity("conversation not created".into()))
    }
    pub fn conversation(&self, project: &str, id: &str) -> Result<Option<Conversation>> {
        self.connection.query_row("SELECT id,project_id,title,created_at FROM chat_conversations WHERE project_id=?1 AND id=?2",params![project,id],|r|Ok(Conversation{id:r.get(0)?,project_id:r.get(1)?,title:r.get(2)?,created_at:r.get(3)?})).optional().map_err(Into::into)
    }
    pub fn conversations(&self, project: &str) -> Result<Vec<Conversation>> {
        Ok(self.connection.prepare("SELECT id,project_id,title,created_at FROM chat_conversations WHERE project_id=?1 ORDER BY rowid DESC")?.query_map([project],|r|Ok(Conversation{id:r.get(0)?,project_id:r.get(1)?,title:r.get(2)?,created_at:r.get(3)?}))?.collect::<std::result::Result<_,_>>()?)
    }
    pub fn conversation_turns(&self, project: &str, session: &str) -> Result<Vec<TurnRecord>> {
        let ids = self
            .connection
            .prepare(
                "SELECT id FROM turns WHERE project_id=?1 AND session_id=?2 ORDER BY ordinal,rowid",
            )?
            .query_map(params![project, session], |r| r.get::<_, String>(0))?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        ids.iter()
            .map(|id| {
                self.turn(id)?
                    .ok_or_else(|| StoreError::Integrity("missing conversation turn".into()))
            })
            .collect()
    }
    pub fn provider_exchange(&self, project: &str, id: &str) -> Result<Option<ProviderExchange>> {
        self.connection
            .query_row(
                "SELECT * FROM provider_exchanges WHERE project_id=?1 AND id=?2",
                params![project, id],
                exchange_row,
            )
            .optional()
            .map_err(Into::into)
    }
    pub fn provider_exchanges(
        &self,
        project: &str,
        session: &str,
    ) -> Result<Vec<ProviderExchange>> {
        Ok(self.connection.prepare("SELECT * FROM provider_exchanges WHERE project_id=?1 AND session_id=?2 ORDER BY rowid")?.query_map(params![project,session],exchange_row)?.collect::<std::result::Result<_,_>>()?)
    }
    pub fn prepare_provider_exchange(&self, record: &ProviderExchange) -> Result<()> {
        self.connection.execute("INSERT INTO provider_exchanges VALUES(?1,?2,?3,?4,?5,?6,?7,?8,'prepared',NULL,NULL,0,?9)",params![record.id,record.project_id,record.session_id,record.packet_digest,record.user_draft,record.prompt,record.prompt_hash,record.ordinal,record.created_at])?;
        Ok(())
    }
    pub fn claim_provider_exchange(
        &self,
        record: &ProviderExchange,
        confirmed_hash: &str,
    ) -> Result<bool> {
        if record.prompt_hash != confirmed_hash
            || canonical_sha256(&record.prompt)? != confirmed_hash
        {
            return Err(StoreError::Integrity(
                "send confirmation does not match preview".into(),
            ));
        }
        let context = self
            .context_run_by_digest(&record.project_id, &record.packet_digest)?
            .ok_or_else(|| StoreError::Integrity("prepared context missing".into()))?;
        let project = self
            .project(&record.project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(record.project_id.clone()))?;
        let next = self
            .conversation_turns(&record.project_id, &record.session_id)?
            .last()
            .map_or(1, |t| t.ordinal + 1);
        if context.provider_session_id != record.session_id
            || project.status != "active"
            || context.draft_hash != canonical_sha256(&record.user_draft)?
            || project.state_version != context.state_version
            || next != record.ordinal
        {
            return Err(StoreError::Integrity(
                "conversation or state changed; preview again".into(),
            ));
        }
        Ok(self.connection.execute("UPDATE provider_exchanges SET status='sending' WHERE id=?1 AND project_id=?2 AND status='prepared'",params![record.id,record.project_id])? == 1)
    }
    pub fn update_provider_exchange(
        &self,
        project: &str,
        id: &str,
        status: &str,
        response: Option<&str>,
        error: Option<&str>,
    ) -> Result<()> {
        self.connection.execute("UPDATE provider_exchanges SET status=?3,response_text=COALESCE(?4,response_text),error_code=?5 WHERE project_id=?1 AND id=?2",params![project,id,status,response,error])?;
        Ok(())
    }
    pub fn accept_reviewed_exchange(&self, project: &str, id: &str) -> Result<()> {
        self.connection.execute("UPDATE provider_exchanges SET accepted_review=1 WHERE project_id=?1 AND id=?2 AND response_text IS NOT NULL",params![project,id])?;
        Ok(())
    }
    pub fn reviewed_exchange_accepted(&self, sent_id: &str) -> Result<bool> {
        Ok(self
            .connection
            .query_row(
                "SELECT accepted_review FROM provider_exchanges WHERE id || ':user'=?1",
                [sent_id],
                |r| r.get::<_, bool>(0),
            )
            .optional()?
            .unwrap_or(false))
    }
    pub fn conversation_view(&self, project: &str, id: &str) -> Result<Value> {
        let session = self.conversation(project, id)?.ok_or_else(|| {
            StoreError::Integrity("conversation does not belong to project".into())
        })?;
        let exchanges = self.provider_exchanges(project,id)?.into_iter().map(|e| {
            let evaluation_id = canonical_sha256(&json!({"kind":"evaluation","turn_id":e.response_id(),"packet_digest":e.packet_digest}))?;
            Ok(json!({"exchange":e,"evaluation":self.response_evaluation(&evaluation_id)?,"commit":self.runtime_commit_for_sent(&e.sent_id())?,"self_report":self.self_report(project,&e.id)?}))
        }).collect::<Result<Vec<Value>>>()?;
        Ok(
            json!({"session":session,"turns":self.conversation_turns(project,id)?,"exchanges":exchanges,"interventions":self.interventions(project)?}),
        )
    }
}

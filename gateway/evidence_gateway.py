#!/usr/bin/env python3
"""Versioned evidence-backed gateway without mutating the frozen WP-29 gateway.

``gateway.tom_gateway`` remains byte-identical to the pilot-v4 code freeze.
This entry point subclasses its runtime and changes behavior only when the
explicit ``shadow`` or ``authoritative`` structure mode is selected.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gateway.tom_gateway as base
from gateway.permanent_library import content_hash
from gateway.shadow_retrieval import (
    build_shadow_comparison,
    dense_channel_with_unscored_tail,
    fuse_ranked_channels,
    structural_channel,
)
from gateway.structural_analysis import (
    COMPILER_VERSION,
    DISALLOWED_ZERO_KINDS,
    EMBEDDING_VERSION,
    LOAD_EVIDENCE_POLICY,
    STRICT_POSITIVE_LOAD_POLICY,
    build_analysis,
    evidenced_load_policy_result,
    rank_structural_history,
    require_evidenced_load,
    require_strictly_positive_load,
    strictly_positive_load_policy_result,
    validate_frozen_analysis,
)


EVIDENCE_GATEWAY_VERSION = "tom-gateway-evidence/1.2"


class EvidenceProjectRuntime(base.ProjectRuntime):
    def __init__(
        self,
        project_id: str,
        state_dir: Path,
        runtime_sha: str,
        seed: base.SeedConfiguration,
        structure_mode: str,
        structure_provider: Any | None,
    ) -> None:
        super().__init__(project_id, state_dir, runtime_sha, seed)
        self.structure_mode = structure_mode
        self.structure_provider = structure_provider

    def _active_structural_history(self) -> list[dict[str, Any]]:
        return self.library.structural_history(self._idempotency.keys())

    def _build_structural_analysis(self, text: str, checkpoint_digest: str) -> dict[str, Any]:
        if self.structure_provider is None:
            raise ValueError("local structural provider is unavailable")
        proposed = self.structure_provider.analyze(text)
        analysis = build_analysis(
            text,
            proposed.get("chunk_candidates"),
            proposed.get("semantic_profile"),
            proposed.get("parser_model"),
            self._active_structural_history(),
            checkpoint_digest,
        )
        if self.structure_mode == "authoritative":
            require_evidenced_load(analysis)
            require_strictly_positive_load(
                analysis["load_signature"],
                name="authoritative 17-channel load",
            )
        return analysis

    def memory_diagnostics(self, after=0):
        result = super().memory_diagnostics(after)
        return {
            **result,
            "structural_load_mode": self.structure_mode,
            "structural_commit_count": len(self._active_structural_history()),
        }

    def preview_rank(self, user_text: str, k: int, max_chars: int) -> dict[str, Any]:
        if self.structure_mode == "legacy":
            return super().preview_rank(user_text, k, max_chars)
        with self.lock:
            triggers = base._compute_preview_triggers(len(self._idempotency))
            checkpoint_digest = self._current_checkpoint_digest()
            analysis = self._build_structural_analysis(user_text, checkpoint_digest)
            if self.structure_mode == "authoritative":
                from agency.mechanics.preview_readout import (
                    load_signature_120_readout_angle,
                    project_load_signature_to_channel_separated_basis,
                )
                from agency.mechanics.sicd_msr_load import LoadSignature

                signature = LoadSignature.from_mapping(analysis["load_signature"], strict=True)
                projection = project_load_signature_to_channel_separated_basis(signature)
                angle = load_signature_120_readout_angle(signature)
            else:
                signature, projection, angle = base.project_text(user_text)
            cohort, branch_trace = base.select_cohort(self.engine.state.branches, signature)
            lexical = self.rgm.vector_store.query(
                user_text, k=max(1, len(self.rgm.state.anchors))
            )
            structural_history = self._active_structural_history()
            structural_rows = rank_structural_history(
                analysis["candidate"], analysis["semantic_profile"],
                structural_history,
            )
            candidates = lexical
            semantic_ranking = None
            if self.structure_mode == "authoritative":
                semantic_ranking = dense_channel_with_unscored_tail(
                    self.rgm.state.anchors, lexical, structural_rows
                )
                authoritative_structural = structural_channel(
                    self.rgm.state.anchors, cohort
                )
                fused = fuse_ranked_channels(
                    semantic_ranking["ranking"], authoritative_structural
                )
            else:
                fused = base.fuse_anchors(self.rgm.state.anchors, candidates, cohort)
            shadow_comparison = None
            if self.structure_mode == "shadow":
                shadow_comparison = build_shadow_comparison(
                    branches=self.engine.state.branches,
                    records=self.rgm.state.anchors,
                    lexical=lexical,
                    current_cohort=cohort,
                    current_fused=fused,
                    evidence_load_signature=analysis["load_signature"],
                    structural_history=structural_history,
                    structural_rows=structural_rows,
                )
            ranked: list[dict[str, Any]] = []
            used_chars = 0
            for scores in fused:
                record_id = scores["id"]
                record = self.rgm.state.anchors.get(record_id)
                if record is None:
                    continue
                text = str(record.content_summary or record.content or "")
                if not text:
                    continue
                remaining = max_chars - used_chars
                if remaining <= 0:
                    break
                bounded = text[:remaining]
                used_chars += len(bounded)
                ranked.append({
                    "id": str(record_id), "text": bounded, **scores,
                    "dependency_relevance": 0.0,
                    "authority_strength": 1.0 if record.policy_outcome.value == "permit" else 0.0,
                })
                if len(ranked) >= k:
                    break
            activation_id = base.canonical_digest({
                "project_id": self.project_id,
                "user_text": user_text,
                "k": k,
                "max_chars": max_chars,
                "checkpoint_digest": checkpoint_digest,
                "structural_analysis_digest": analysis["analysis_digest"],
            })
            result = {
                "activation_id": activation_id,
                "triggers": [asdict(trigger) for trigger in triggers],
                "ranked_anchors": ranked,
                "activated_branch_ids": [bid for bid, _, _ in cohort],
                "candidate_trace": fused,
                "branch_trace": branch_trace,
                "load_signature": signature.as_dict(),
                "structural_load_mode": self.structure_mode,
                "structural_analysis": analysis,
                "load_evidence_policy_result": evidenced_load_policy_result(analysis),
                "strict_positive_load_policy_result": (
                    strictly_positive_load_policy_result(analysis["load_signature"])
                ),
                "shadow_structural_retrieval": structural_rows,
                "policy_version": base.POLICY_VERSION,
                "checkpoint_digest": checkpoint_digest,
            }
            if semantic_ranking is not None:
                result["structural_semantic_ranking"] = semantic_ranking
            if shadow_comparison is not None:
                result["shadow_retrieval_comparison"] = shadow_comparison
            return result

    def commit_turn(
        self,
        role: str,
        text: str,
        idempotency_key: str,
        *,
        response_text=None,
        activated_branch_ids=(),
        admitted_anchor_ids=(),
        conflict_dismissed=False,
        packet_digest=None,
        structural_analysis=None,
    ) -> dict[str, Any]:
        if self.structure_mode == "legacy":
            return super().commit_turn(
                role, text, idempotency_key,
                response_text=response_text,
                activated_branch_ids=activated_branch_ids,
                admitted_anchor_ids=admitted_anchor_ids,
                conflict_dismissed=conflict_dismissed,
                packet_digest=packet_digest,
            )
        from gateway.front_row import FrontRowMemory
        from memory.rgm import MemoryRecord, PolicyOutcome

        with self.lock:
            if idempotency_key in self._idempotency:
                return self._idempotency[idempotency_key]
            if not text or type(conflict_dismissed) is not bool:
                raise ValueError("nonempty committed text and boolean conflict_dismissed required")
            branch_ids = sorted(set(str(bid) for bid in activated_branch_ids))
            anchor_ids = sorted(set(str(rid) for rid in admitted_anchor_ids))
            for bid in branch_ids:
                if bid not in self.engine.state.branches:
                    raise ValueError(f"sent packet branch no longer exists: {bid}")
            for rid in anchor_ids:
                if self.library.get(rid) is None:
                    raise ValueError(f"sent packet anchor has no durable twin: {rid}")
            if response_text is None and role == "assistant":
                response_text = text
            stored_text = text if response_text is None or role == "assistant" else (
                "USER\n" + text + "\nASSISTANT\n" + response_text
            )
            before_tick = int(self.engine.state.tick)
            prior_digest = self._current_checkpoint_digest()
            if structural_analysis is None:
                raise ValueError("prepared structural analysis is required; prepare again")
            analysis = validate_frozen_analysis(
                structural_analysis,
                text,
                self._active_structural_history(),
                prior_digest,
            )
            if self.structure_mode == "authoritative":
                from agency.mechanics.sicd_msr_load import LoadSignature
                require_evidenced_load(analysis)
                require_strictly_positive_load(
                    analysis["load_signature"],
                    name="authoritative 17-channel load",
                )
                applied_signature = LoadSignature.from_mapping(
                    analysis["load_signature"], strict=True
                )
            else:
                applied_signature = base.project_text(text)[0]
            anchor_id = "turn-" + hashlib.sha256(
                f"{self.project_id}\0{idempotency_key}".encode("utf-8")
            ).hexdigest()[:32]
            anchor_id = self.library.first_id_for_hash(content_hash(stored_text)) or anchor_id
            record = MemoryRecord(
                id=anchor_id,
                content=stored_text,
                content_summary=stored_text,
                content_hash=content_hash(stored_text),
                anchor_type="conversation_turn",
                anchor_strength=1.0,
                decay_rate=0.002,
                novelty_score=1.0,
                S=1.0,
                C=1.0,
                H=0.0,
                sensitivity="low",
                policy_outcome=PolicyOutcome.PERMIT,
                policy_version="tom-assist-commit/1.2-evidence",
                model="direct-engine",
                source="tom_assist_committed_exchange",
                semantic_tags=[role, f"project:{self.project_id}"],
                created_tick=before_tick + 1,
            )
            if self.structure_mode == "authoritative":
                from agency.mechanics.sicd_msr_routing_basis import (
                    project_load_signature_to_routing_basis,
                )
                record.leaf_vec = list(
                    project_load_signature_to_routing_basis(applied_signature).vector_8d
                )
            else:
                record.leaf_vec = list(base.project_text(stored_text)[1].vector_8d)
            self.library.retain(record, self.rgm._record_to_dict(record))
            prior_engine, prior_rgm = self.engine, self.rgm
            prior_idempotency = dict(self._idempotency)
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                head = self.library.head()
                durable_idempotency = json.loads(head[2])
                if idempotency_key in durable_idempotency:
                    self.library.db.execute("ROLLBACK")
                    self._idempotency = durable_idempotency
                    self._write_head_artifacts(head)
                    self.settings = json.loads(head[3])
                    self._restore_current_artifacts_if_present()
                    return durable_idempotency[idempotency_key]
                if base.canonical_digest(self._artifact_payload(head[0], head[1])) != prior_digest:
                    raise ValueError("runtime advanced in another process; reopen before committing")
                self.engine = copy.deepcopy(prior_engine)
                self.rgm = FrontRowMemory(self.library, self.settings["front_row_capacity"])
                self.rgm.restore(prior_rgm.serialize())
                self.rgm.state = copy.deepcopy(prior_rgm.state)
                from agency.mechanics.sicd_msr_load_application import (
                    apply_msr_load_to_sicd_engine,
                )
                application = apply_msr_load_to_sicd_engine(
                    self.engine,
                    applied_signature,
                    source="tom_assist_committed_exchange",
                )
                if not application.applied:
                    raise ValueError(f"canonical commit drive refused load: {application.reason}")
                stored_id = self.rgm.write(record)
                if stored_id == "deferred":
                    raise ValueError("committed exchange RGM admission refused")
                taught = False
                teach_reason = "no_provider_response"
                if response_text is not None:
                    teach_reason = (
                        "conflict_dismissed_policy"
                        if conflict_dismissed and not self.settings["teach_on_conflict"]
                        else "confidence_gate"
                    )
                    if teach_reason != "conflict_dismissed_policy":
                        projection = base.project_text(response_text)[1]
                        raw_response = projection.raw_8d
                        llm_output = {
                            "semantic_axis": list(raw_response[:3]),
                            "loads": dict(zip(
                                ("delta_x", "delta_F", "phi", "intensity"),
                                raw_response[3:7],
                            )),
                            "confidence": raw_response[7],
                        }
                        if not self.engine.cfg.kappa_update.enable_leaf_vec:
                            raise ValueError("commit teaching requires enabled leaf vectors")
                        self.engine.apply_leaf_vec_update(llm_output)
                        taught = self.engine.state.last_leaf_vec_update_tick == self.engine.state.tick
                        if (
                            raw_response[7] >= self.engine.cfg.kappa_update.leaf_vec_confidence_gate
                            and not taught
                        ):
                            raise ValueError("confident leaf-vector teaching did not complete")
                        if taught:
                            teach_reason = "committed_response"
                for bid in branch_ids:
                    if bid not in self.engine.state.branches:
                        raise ValueError(f"physics removed a serving branch; prepare again: {bid}")
                    self.engine.state.branches[bid].usage_count += 1
                readmitted_ids = self.rgm.reseat(anchor_ids, idempotency_key)
                self.library.retain_structural_commit(
                    idempotency_key, stored_id, analysis, int(self.engine.state.tick)
                )
                tree_bytes, rgm_bytes = self.serialized_state_bytes()
                checkpoint_digest = base.canonical_digest(
                    self._artifact_payload(tree_bytes, rgm_bytes)
                )
                result = {
                    "idempotency_key": idempotency_key,
                    "role": role,
                    "text_hash": base.canonical_digest(text),
                    "engine_tick_before": before_tick,
                    "engine_tick_after": int(self.engine.state.tick),
                    "rgm_current_tick": int(self.rgm.state.current_tick),
                    "branch_count": len(self.engine.state.branches),
                    "anchor_id": stored_id,
                    "K_total": float(application.kappa_total_after or 0.0),
                    "runtime_error_code": None,
                    "seed_profile": self.creation_metadata.get("seed_profile"),
                    "seed_checkpoint_digest": self.creation_metadata.get("initial_checkpoint_digest"),
                    "prior_checkpoint_digest": prior_digest,
                    "checkpoint_digest": checkpoint_digest,
                    "commit_dynamics": list(base.COMMIT_DYNAMICS),
                    "taught": taught,
                    "teach_reason": teach_reason,
                    "commit_drive": application.as_dict(),
                    "structural_load": {
                        "mode": self.structure_mode,
                        "compiler_version": analysis["compiler_version"],
                        "analysis_digest": analysis["analysis_digest"],
                        "candidate_digest": analysis["candidate_digest"],
                        "load_signature": applied_signature.as_dict(),
                        "candidate_load_signature": analysis["load_signature"],
                        "channel_records": analysis["channel_records"],
                        "load_evidence_policy_result": evidenced_load_policy_result(
                            analysis
                        ),
                        "strict_positive_load_policy_result": (
                            strictly_positive_load_policy_result(
                                analysis["load_signature"]
                            )
                        ),
                        "orientation_count": len(analysis["candidate"]["orientations"]),
                        "causal_relation_count": len(analysis["candidate"]["causal_relations"]),
                        "history_metrics": analysis["history_metrics"],
                    },
                    "activated_branch_ids": branch_ids,
                    "admitted_anchor_ids": anchor_ids,
                    "readmitted_anchor_ids": readmitted_ids,
                    "packet_digest": packet_digest,
                }
                self._idempotency[idempotency_key] = result
                self.library.set_head(tree_bytes, rgm_bytes, self._idempotency, self.settings)
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                self.engine, self.rgm = prior_engine, prior_rgm
                self._idempotency = prior_idempotency
                self._checkpoint_digest = prior_digest
                raise
            self._checkpoint_digest = checkpoint_digest
            try:
                self._write_head_artifacts(self.library.head())
            except OSError:
                base.LOGGER.exception(
                    "committed runtime head is durable; JSON projection needs recovery"
                )
            return result


class EvidenceTomGateway(base.TomGateway):
    project_runtime_class = EvidenceProjectRuntime

    def __init__(
        self,
        data_dir: Path = base.DEFAULT_DATA_DIR,
        tom_master: Path = base.DEFAULT_TOM_MASTER,
        *,
        seed_artifact: Path | None = None,
        mechanics_profile: Path | None = None,
        structure_mode: str | None = None,
        structure_provider: Any | None = None,
    ) -> None:
        super().__init__(
            data_dir,
            tom_master,
            seed_artifact=seed_artifact,
            mechanics_profile=mechanics_profile,
        )
        self.structure_mode = str(
            structure_mode if structure_mode is not None
            else os.environ.get("TOM_ASSIST_STRUCTURE_MODE", "legacy")
        ).strip().lower()
        if self.structure_mode not in {"legacy", "shadow", "authoritative"}:
            raise ValueError("TOM_ASSIST_STRUCTURE_MODE must be legacy, shadow, or authoritative")
        if self.structure_mode != "legacy" and structure_provider is None:
            from gateway.structure_provider import StructureWorkerClient
            structure_provider = StructureWorkerClient.from_environment()
        self.structure_provider = structure_provider

    def create_project_runtime(self, project_id: str, state_dir: Path):
        return EvidenceProjectRuntime(
            project_id, state_dir, self.runtime_sha, self.seed,
            self.structure_mode, self.structure_provider,
        )

    def project(self, project_id: Any) -> EvidenceProjectRuntime:
        project_id = base._safe_project_id(project_id)
        with self._projects_lock:
            runtime = self._projects.get(project_id)
            if runtime is None:
                from gateway.runtime_archive import finalize_pending
                finalize_pending(self.data_dir / "projects" / project_id)
                runtime = self.create_project_runtime(
                    project_id,
                    self.data_dir / "projects" / project_id / "tom",
                )
                self._projects[project_id] = runtime
            return runtime

    def capabilities(self) -> dict[str, Any]:
        return {
            **super().capabilities(),
            "structural_load_mode": self.structure_mode,
            "structural_load_compiler_version": COMPILER_VERSION,
            "load_evidence_policy": LOAD_EVIDENCE_POLICY,
            "authoritative_requires_all_17_channels_evidenced": True,
            "authoritative_disallowed_zero_kinds": sorted(DISALLOWED_ZERO_KINDS),
            "strict_positive_load_policy": STRICT_POSITIVE_LOAD_POLICY,
            "authoritative_requires_all_17_channels_positive": True,
            "semantic_embedding_version": EMBEDDING_VERSION,
            "local_gemma_candidate_required": self.structure_mode != "legacy",
            "model_generated_load_values": False,
            "feeling_wheel_used": False,
        }

    def handle(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        payload = payload or {}
        if method == "GET" and path == "/health":
            status, response = super().handle(method, path, payload)
            return status, {**response, "gateway_version": EVIDENCE_GATEWAY_VERSION}
        if method == "POST" and path == "/turn/commit":
            try:
                key = str(payload.get("idempotency_key") or "")
                if not key:
                    raise ValueError("idempotency_key is required")
                return 200, self.project(payload.get("project_id")).commit_turn(
                    str(payload.get("role") or "user"),
                    str(payload.get("text") or ""),
                    key,
                    response_text=payload.get("response_text"),
                    activated_branch_ids=payload.get("activated_branch_ids") or [],
                    admitted_anchor_ids=payload.get("admitted_anchor_ids") or [],
                    conflict_dismissed=payload.get("conflict_dismissed", False),
                    packet_digest=payload.get("packet_digest"),
                    structural_analysis=payload.get("structural_analysis"),
                )
            except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as error:
                return 400, {"error": error.__class__.__name__, "message": str(error)}
            except Exception as error:
                base.LOGGER.exception("evidence gateway commit failed")
                return 500, {"error": error.__class__.__name__, "message": str(error)[:500]}
        return super().handle(method, path, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=base.DEFAULT_DATA_DIR)
    parser.add_argument("--tom-master", type=Path, default=base.DEFAULT_TOM_MASTER)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    base.serve(
        args.socket,
        EvidenceTomGateway(args.data_dir, args.tom_master),
    )


if __name__ == "__main__":
    main()

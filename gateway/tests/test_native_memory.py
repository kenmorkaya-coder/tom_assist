"""Native memory integration boundaries; small fixtures, no local models loaded."""
import hashlib
import json
import types
import pytest
from gateway.tom_gateway import TomGateway


def _rgm_heading_count_result():
    record = dict(decision="verified", intent_class="hard_fact_numeric", reply="section_4_count is 3",
        chat_would_return_before_llm=True, telemetry=dict(active_doc_ids=["document-a"], decision="VERIFIED"))
    evidence = [dict(heading_path="SEI:document-a:section_4",
        extracted_value=dict(key="section_4_count", value_token="3"))]
    return record, evidence


@pytest.mark.parametrize("question", [
    "Who has the duty to fund premiums and other policy charges for the insurance in clause 23.1?",
    "For the policies in clause 23.1, explain both the responsibility for paying premiums and the responsibility for policy deductibles.",
    "Who pays under section 4?", "How many premiums must be paid under section 4?",
    "How many subsections are under section 23.1?", "How many subheadings are there?",
    "How many subsections are under section 4 and who pays the premiums?",
    "Do not count the subsections under section 4.",
])
def test_rgm_heading_count_rejects_wrong_answer_type_target_and_compound_requests(question):
    from gateway.native_memory import guard_rgm_heading_count
    record, evidence = _rgm_heading_count_result()
    original = json.dumps([record, evidence], sort_keys=True)
    result = guard_rgm_heading_count(question, record, evidence)
    assert result["decision"] == "needs_evidence_reading"
    assert result["reply"] is None
    assert result["chat_would_return_before_llm"] is False
    assert result["upstream_policy"] == record
    assert json.dumps([record, evidence], sort_keys=True) == original


@pytest.mark.parametrize("question", [
    "How many subsections are in section 4?", "How many subheadings does section 4 have?",
    "Count the subheadings under section 4.", "What is the number of subsections in section 4?",
    "What is section_4_count?",
])
def test_rgm_heading_count_preserves_explicit_matching_count_requests(question):
    from gateway.native_memory import guard_rgm_heading_count
    record, evidence = _rgm_heading_count_result()
    result = guard_rgm_heading_count(question, record, evidence)
    assert result["decision"] == "verified" and result["reply"] == record["reply"]
    assert result["heading_count_check"]["status"] == "request_matches"


@pytest.mark.parametrize("damage", ["wrong_document", "ambiguous_documents", "wrong_source_section", "multiple_answers"])
def test_rgm_heading_count_requires_the_counted_section_and_active_document(damage):
    from gateway.native_memory import guard_rgm_heading_count
    record, evidence = _rgm_heading_count_result()
    if damage == "wrong_document": record["telemetry"]["active_doc_ids"] = ["document-b"]
    elif damage == "ambiguous_documents": record["telemetry"]["active_doc_ids"].append("document-b")
    elif damage == "wrong_source_section": evidence[0]["heading_path"] = "SEI:document-a:section_23"
    else: evidence.append(dict(evidence[0]))
    assert guard_rgm_heading_count("How many subsections are under section 4?", record, evidence)["decision"] == "needs_evidence_reading"


def test_rgm_heading_count_does_not_replace_non_count_or_unverified_results():
    from gateway.native_memory import guard_rgm_heading_count
    record, evidence = _rgm_heading_count_result()
    evidence[0]["extracted_value"]["key"] = "premium_amount"
    assert guard_rgm_heading_count("What is the premium?", record, evidence) == record
    record["decision"] = "not_found"
    assert guard_rgm_heading_count("Who pays?", record, evidence) == record


def _native_answer_profile(count=3):
    from gateway.native_memory import EVIDENCE_ROLE_FIELDS, QUESTION_PRECISION_INSTRUCTION
    registry = []
    for i in range(count):
        text = f"Party {i} must not omit the inspection."
        start = i * 100; end = start + len(text); pdf_sha = "a" * 64
        sid = "SRC-" + hashlib.sha256(f"sha256:{pdf_sha}:{start}:{end}".encode()).hexdigest()[:16]
        registry.append(dict(source_id=sid, text=text, provenance=dict(start=start, end=end,
            source_text=text, pdf_sha256=pdf_sha, clause=str(i + 1), pdf_page=i + 1)))
    return dict(version="tom-assist-native-memory-profile/1", project_id="native-project",
        registry=registry, source_roles={s["source_id"]: {k: None for k in ("request", *EVIDENCE_ROLE_FIELDS)} for s in registry},
        checkpoint=dict(state_hash="frozen-tree"), scope="Boundary fixture only",
        question_instruction_sha256=hashlib.sha256(QUESTION_PRECISION_INSTRUCTION.encode()).hexdigest())


def _reviewed_rgm_situation():
    from gateway.native_memory import EVIDENCE_ROLE_FIELDS, rgm_role_record_receipt
    text = ("If TfNSW fails to demonstrate insurance compliance, SM may obtain replacement cover. "
            "TfNSW must reimburse SM on demand.")
    digest = hashlib.sha256(text.encode()).hexdigest()
    source = dict(source_id="SRC-reviewed", text=text, provenance=dict(
        document_id="document-contract", chunk_id="chunk-23-5", clause="23.5",
        start=100, end=100 + len(text), source_text=text,
        extracted_text_sha256=digest))
    roles = {key: None for key in EVIDENCE_ROLE_FIELDS}
    roles.update(request=None, failure_party="TfNSW", cover_payer="SM",
        repayment_from="TfNSW", repayment_to="SM", repayment_when="on demand")
    verification = dict(status="frozen_verified", method="reviewed role-bound source record",
        role_record_sha256=rgm_role_record_receipt(source, roles))
    return source, roles, verification


def test_reviewed_rgm_situation_survives_native_write_and_reload():
    from gateway.native_memory import build_rgm_situation_memory, read_rgm_situation_memory
    from gateway.vendor.rgm17d.memory.rgm import ReflectionGatedMemory
    source, roles, verification = _reviewed_rgm_situation()
    record = build_rgm_situation_memory(source, roles, verification)
    rgm = ReflectionGatedMemory()
    assert rgm.write_memory(record)
    restored = ReflectionGatedMemory()
    restored.restore(rgm.serialize())
    result = read_rgm_situation_memory(next(iter(restored.state.anchors.values())))
    assert result["source_id"] == source["source_id"]
    assert result["provenance"] == source["provenance"]
    assert [(row["kind"], row["source_label"], row["target_label"])
            for row in result["relations"]] == [
        ("triggers_replacement_cover", "TfNSW", "SM"),
        ("reimburses", "TfNSW", "SM"),
    ]


@pytest.mark.parametrize("damage", ["roles", "source_text", "stored_relation"])
def test_reviewed_rgm_situation_rejects_changed_roles_source_or_record(damage):
    from gateway.native_memory import build_rgm_situation_memory, read_rgm_situation_memory
    source, roles, verification = _reviewed_rgm_situation()
    if damage == "roles":
        roles = dict(roles, failure_party="SM", cover_payer="TfNSW")
        with pytest.raises(ValueError, match="reviewed-role receipt"):
            build_rgm_situation_memory(source, roles, verification)
        return
    if damage == "source_text":
        source = dict(source, text=source["text"].replace("must reimburse", "must not reimburse"))
        with pytest.raises(ValueError, match="text and provenance disagree"):
            build_rgm_situation_memory(source, roles, verification)
        return
    record = build_rgm_situation_memory(source, roles, verification)
    record.source_refs[0]["relations"][0]["target"] = record.source_refs[0]["relations"][0]["source"]
    with pytest.raises(ValueError, match="checksum changed"):
        read_rgm_situation_memory(record)


def _rgm_reader_packet():
    text = "23.2 Premiums\nAuthority must pay the premiums, unless the exception applies."
    ref = dict(corpus_id="corpus", chunk_id="chunk_1", doc_id="document", start=100,
        end=100+len(text), text_sha256=hashlib.sha256(text.encode()).hexdigest())
    return dict(memories=[dict(id="chunk_1",content=text,evidence_reference=ref)])


def test_pdf_spacing_repair_returns_original_text_and_absolute_offsets():
    from gateway.document_ingestion import _align_rgm_pdf_quote
    from gateway.native_memory import validate_evidence_reading
    before="9.2 Payment obligation for the required insurance policies.\n"
    quote="Orchid Transit must pay all amounts payable under clause 9.1."
    original=quote.replace("payable","p ayable")
    after="\n9.3 The deductible is a separate obligation."
    text=before+original+after
    source=dict(source_id="source",text=text,provenance=dict(start=200))
    raw=json.dumps(dict(status="supported",source_id="source",answer_quote=quote))
    with pytest.raises(ValueError,match="exact source span"):
        validate_evidence_reading(raw,[source])
    result=validate_evidence_reading(raw,[source],spacing_resolver=lambda s,q:
        _align_rgm_pdf_quote(s["text"],q,before+quote+after))
    assert result["answer_quote"]==original
    assert text[result["local_start"]:result["local_end"]]==original
    assert result["absolute_start"]==200+len(before)
    assert result["absolute_end"]==200+len(before)+len(original)
    assert result["spacing_verification"]["pdf_quote"]==quote


@pytest.mark.parametrize("quote,pdf_quote",[
    ("They are nowhere near the site.","They are now here near the site."),
    ("They remain apart from the group.","They remain a part from the group."),
    ("Orchid must pay 100 dollars.","Orchid must pay 1000 dollars."),
    ("Orchid must pay all premiums.","Orchid must not pay all premiums."),
    ("Cedar must pay all premiums.","Orchid must pay all premiums."),
])
def test_pdf_spacing_repair_preserves_words_numbers_negation_and_actors(quote,pdf_quote):
    from gateway.document_ingestion import _align_rgm_pdf_quote
    prefix="A sufficiently long and unique contextual heading for this paragraph.\n"
    suffix="\nThe next paragraph concerns a distinct insurance obligation."
    with pytest.raises(ValueError):
        _align_rgm_pdf_quote(prefix+pdf_quote+suffix,quote,prefix+pdf_quote+suffix)


@pytest.mark.parametrize("damage",["duplicate_source","duplicate_pdf","wrong_context","changed_letter","short_context"])
def test_pdf_spacing_repair_refuses_ambiguous_or_unverified_locations(damage):
    from gateway.document_ingestion import _align_rgm_pdf_quote
    quote="Orchid must pay premiums payable under clause 9.1."
    prefix="A sufficiently long heading binds this passage to its location.\n"
    source=prefix+quote.replace("payable","p ayable")
    pdf=prefix+quote
    if damage=="duplicate_source":source+=source
    elif damage=="duplicate_pdf":pdf+=pdf
    elif damage=="wrong_context":pdf=pdf.replace("heading","paragraph")
    elif damage=="changed_letter":quote=quote.replace("9.1","9.2")
    else:source=source[len(prefix):];pdf=pdf[len(prefix):]
    with pytest.raises(ValueError):_align_rgm_pdf_quote(source,quote,pdf)


def test_pdf_spacing_resolver_cannot_supply_different_characters():
    from gateway.native_memory import validate_evidence_reading
    source=dict(source_id="source",text="Orchid must not pay.")
    raw=json.dumps(dict(status="supported",source_id="source",answer_quote="Orchid must pay."))
    with pytest.raises(ValueError,match="changed source characters"):
        validate_evidence_reading(raw,[source],spacing_resolver=lambda s,q:dict(start=0,end=len(s["text"])))


def test_pdf_spacing_resolver_requires_matching_document_checksum_and_source_binding(tmp_path,monkeypatch):
    import contextlib
    import sys
    from gateway.document_ingestion import make_rgm_pdf_quote_resolver
    quote="Orchid must pay all amounts payable."
    prefix="Insurance premiums and other policy charges are governed by this clause.\n"
    independent=prefix+quote
    fake=types.SimpleNamespace(__version__="fixture",open=lambda stream:
        contextlib.nullcontext(types.SimpleNamespace(pages=[types.SimpleNamespace(extract_text=lambda:independent)])))
    monkeypatch.setitem(sys.modules,"pdfplumber",fake)
    path=tmp_path/"source.pdf";path.write_bytes(b"checksum fixture, no PDF generated")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match="checksum mismatch"):
        make_rgm_pdf_quote_resolver(path,"0"*64)
    resolve=make_rgm_pdf_quote_resolver(path,digest)
    source=dict(text=independent.replace("payable","p ayable"),
        provenance=dict(provenance=dict(source_pdf_sha256=digest)))
    assert resolve(source,quote)["pdf_page"]==1
    source["provenance"]["provenance"]["source_pdf_sha256"]="0"*64
    with pytest.raises(ValueError,match="not bound"):
        resolve(source,quote)


def _cited_clause_packet():
    text=("9.6 Earlier obligation\nOrchid pays the premiums.\n"
          "9.7 Notice\nCedar must notify Orchid promptly, unless notice was already given.\n"
          "If the policy requires other notices, Cedar must also give those notices.\n"
          "9.8 Next obligation\nOrchid must retain the records.")
    ref=dict(corpus_id="corpus",chunk_id="chunk_1",doc_id="document",start=200,
        end=200+len(text),text_sha256=hashlib.sha256(text.encode()).hexdigest())
    return dict(memories=[dict(id="chunk_1",content=text,evidence_reference=ref)])


def test_rgm_refusal_recheck_reads_the_cited_clause_and_keeps_original_offsets():
    from gateway.native_memory import read_rgm_source_evidence
    packet=_cited_clause_packet();calls=[]
    quote="Cedar must notify Orchid promptly, unless notice was already given."
    def generate(instruction,data,limit):
        calls.append(data)
        if len(calls)==1:return dict(raw=json.dumps(dict(status="not_supported",source_id=None,answer_quote=None)))
        assert len(data["sources"])==1
        assert "unless notice was already given" in data["sources"][0]["text"]
        assert "Earlier obligation" not in data["sources"][0]["text"]
        assert "Next obligation" not in data["sources"][0]["text"]
        return dict(raw=json.dumps(dict(status="supported",source_id="corpus/chunk_1",answer_quote=quote)))
    result=read_rgm_source_evidence("Under clause 9.7, who must notify Orchid?",packet,generate)
    assert result["status"]=="supported" and len(calls)==2
    answer=result["answers"][0];text=packet["memories"][0]["content"]
    assert answer["start"]==200+text.index("9.7 Notice")
    assert answer["text"]==text[answer["start"]-200:answer["end"]-200]
    assert result["parts"][0]["refusal_recheck"]["focus"]["clause"]=="9.7"
    assert result["parts"][0]["refusal_recheck"]["validated_proposal"]["answer_quote"]==quote
    assert answer["text"]==result["parts"][0]["refusal_recheck"]["focus"]["text"]
    assert "If the policy requires other notices" in answer["text"]
    assert json.loads(result["parts"][0]["generation"]["raw"])["status"]=="not_supported"


@pytest.mark.parametrize("quote,source_id",[
    ("Orchid pays the premiums.","corpus/chunk_1"),
    ("Cedar must notify Orchid promptly, unless notice was already given.","other/chunk_1"),
    ("Cedar must pay 100 dollars.","corpus/chunk_1"),
])
def test_rgm_refusal_recheck_rejects_outside_clause_wrong_source_and_invented_text(quote,source_id):
    from gateway.native_memory import read_rgm_source_evidence
    calls=[]
    def generate(*args):
        calls.append(args)
        return dict(raw=json.dumps(dict(status="not_supported",source_id=None,answer_quote=None) if len(calls)==1
            else dict(status="supported",source_id=source_id,answer_quote=quote)))
    result=read_rgm_source_evidence("Under clause 9.7, who gives notice?",_cited_clause_packet(),generate)
    assert result["status"]=="invalid" and len(calls)==2


@pytest.mark.parametrize("question",["Who gives notice?","Under clause 8.7, who gives notice?",
    "Under clauses 9.6 and 9.7, who pays?","Under clause 9.7 and 9.6, who pays?",
    "Under clause 9.8, who retains records?"])
def test_rgm_refusal_recheck_does_not_guess_missing_ambiguous_or_unbounded_clauses(question):
    from gateway.native_memory import read_rgm_source_evidence
    calls=[]
    def generate(*args):
        calls.append(args);return dict(raw='{"status":"not_supported","source_id":null,"answer_quote":null}')
    result=read_rgm_source_evidence(question,_cited_clause_packet(),generate)
    assert result["status"]=="not_supported" and len(calls)==1


def test_rgm_refusal_recheck_does_not_choose_between_duplicate_clause_numbers():
    from gateway.native_memory import find_rgm_cited_clause
    text=_cited_clause_packet()["memories"][0]["content"]
    assert find_rgm_cited_clause("Under clause 9.7, who gives notice?",[
        dict(source_id="a",text=text),dict(source_id="b",text=text)]) is None


def test_rgm_refusal_recheck_stops_after_one_unsuccessful_reading():
    from gateway.native_memory import read_rgm_source_evidence
    calls=[]
    def generate(*args):
        calls.append(args);return dict(raw='{"status":"not_supported","source_id":null,"answer_quote":null}')
    result=read_rgm_source_evidence("Under clause 9.7, what is the policy number?",_cited_clause_packet(),generate)
    assert result["status"]=="not_supported" and len(calls)==2


def _replacement_chain_source(**changes):
    roles=dict(failure_party="Cedar Authority",cover_payer="Orchid Transit",
               repayment_from="Cedar Authority",repayment_to="Orchid Transit")
    roles.update(changes)
    text=(f"9.5 Evidence of compliance\n(a) If, within 30 Business Days, {roles['failure_party']} fails to\n"
        f"provide evidence of compliance, {roles['cover_payer']} may, without prejudice to other remedies\n"
        f"available to {roles['cover_payer']}, effect and maintain that insurance and pay the premiums.\n"
        f"(b) Any amounts paid by {roles['cover_payer']} under clause 9.5(a) will be a debt due from\n"
        f"{roles['repayment_from']} to {roles['repayment_to']} and {roles['repayment_from']} must reimburse\n"
        f"{roles['repayment_to']} for such amount on demand.\n")
    return dict(source_id="source",text=text)


CHAIN_QUESTION = ("Which clause requires Cedar Authority to reimburse Orchid Transit when Orchid Transit bought "
    "replacement cover following Cedar Authority’s failure to demonstrate compliance?")


@pytest.mark.parametrize("field", ["failure_party","cover_payer","repayment_from","repayment_to"])
def test_rgm_replacement_chain_checks_each_role_independently(field):
    from gateway.native_memory import check_rgm_replacement_chain
    source=_replacement_chain_source()
    correct=check_rgm_replacement_chain(CHAIN_QUESTION,[source])
    assert correct["status"] == "supported"
    for span in correct["chains"][0]["relation_spans"]:
        assert source["text"][span["start"]:span["end"]] == span["text"]
    changed=check_rgm_replacement_chain(CHAIN_QUESTION,[_replacement_chain_source(**{field:"Harbour Agency"})])
    assert changed["status"] == "not_supported"
    assert changed["chains"][0]["mismatches"] == [field]


def test_rgm_replacement_chain_never_combines_roles_from_different_clauses():
    from gateway.native_memory import check_rgm_replacement_chain
    a=_replacement_chain_source(repayment_from="Orchid Transit",repayment_to="Cedar Authority")
    b=_replacement_chain_source(failure_party="Orchid Transit",cover_payer="Cedar Authority")
    b["source_id"]="second"
    result=check_rgm_replacement_chain(CHAIN_QUESTION,[a,b])
    assert result["status"] == "not_supported"
    assert [c["mismatches"] for c in result["chains"]] == [["repayment_from","repayment_to"],["failure_party","cover_payer"]]


@pytest.mark.parametrize("damage", ["wrong_link","missing_condition","negative","extra_condition","missing_heading","missing_subsection","extra_subsection"])
def test_rgm_replacement_chain_leaves_incomplete_or_qualified_evidence_unverified(damage):
    from gateway.native_memory import check_rgm_replacement_chain
    source=_replacement_chain_source()
    if damage=="wrong_link":source["text"]=source["text"].replace("clause 9.5(a)","clause 9.6(a)")
    elif damage=="missing_condition":source["text"]=source["text"].replace("fails to", "has not shown how to")
    elif damage=="negative":source["text"]=source["text"].replace("must reimburse", "must not reimburse")
    elif damage=="extra_condition":source["text"] += "This applies only if an additional agreement is signed."
    elif damage=="missing_subsection":source["text"]=source["text"].replace("(a)","(c)",1)
    elif damage=="extra_subsection":source["text"] += "(c) A further condition also applies."
    else:source["text"]=source["text"].split("\n",1)[1]
    assert check_rgm_replacement_chain(CHAIN_QUESTION,[source])["status"] == "needs_evidence_reading"


def test_rgm_replacement_chain_ambiguous_sources_and_unknown_question_are_not_forced():
    from gateway.native_memory import check_rgm_replacement_chain
    source=_replacement_chain_source()
    assert check_rgm_replacement_chain(CHAIN_QUESTION,[source,dict(source,source_id="duplicate")])["status"] == "ambiguous"
    assert check_rgm_replacement_chain("Who reimburses whom for replacement cover?",[source])["status"] == "needs_evidence_reading"
    assert check_rgm_replacement_chain("Who pays premiums?",[source])["status"] == "not_applicable"
    assert check_rgm_replacement_chain(CHAIN_QUESTION.replace("when","only when"),[source])["status"] == "needs_evidence_reading"


@pytest.mark.parametrize("question,expected", [
    ("If Transport for NSW does not prove its insurance compliance after a written request, can Sydney Metro arrange the insurance itself, and who has to repay the cost?", "tfnsw"),
    ("If Sydney Metro does not prove its insurance compliance after a written request, can Transport for NSW arrange the insurance itself, and who has to repay the cost?", "sm"),
])
def test_rgm_replacement_chain_distinguishes_mirrored_abbreviated_parties(question, expected):
    from gateway.native_memory import check_rgm_replacement_chain
    tfnsw = _replacement_chain_source(failure_party="TfNSW", cover_payer="SM",
        repayment_from="TfNSW", repayment_to="SM")
    tfnsw["source_id"] = "tfnsw"
    sm = _replacement_chain_source(failure_party="SM", cover_payer="TfNSW",
        repayment_from="SM", repayment_to="TfNSW")
    sm["source_id"] = "sm"
    result = check_rgm_replacement_chain(question, [tfnsw, sm])
    assert result["status"] == "supported"
    assert result["matches"][0]["source_id"] == expected
    assert result["matches"][0]["mismatches"] == []


@pytest.mark.parametrize("question,expected", [
    ("If Transport for NSW does not prove its insurance compliance, can Sydney Metro arrange the insurance, and who repays the cost?",
        dict(failure_party="TfNSW", cover_payer="SM")),
    ("If Sydney Metro does not prove its insurance compliance, can Transport for NSW arrange the insurance, and who repays the cost?",
        dict(failure_party="SM", cover_payer="TfNSW")),
])
def test_reviewed_query_situation_resolves_mirrored_aliases_without_source_evidence(question, expected):
    from gateway.native_memory import reviewed_query_situation
    memories = [dict(relation_kind="replacement_cover", source_party="TfNSW", target_party="SM"),
        dict(relation_kind="replacement_cover", source_party="SM", target_party="TfNSW")]
    result = reviewed_query_situation(question, memories)
    assert result["status"] == "complete"
    assert result["fields"] == dict(relation_kind="replacement_cover",
        source_party=expected["failure_party"], target_party=expected["cover_payer"])


@pytest.mark.parametrize("question,expected", [
    ("Does Transport for NSW reimburse Sydney Metro?", ("TfNSW", "SM")),
    ("Which clause says Sydney Metro repays Transport for NSW?", ("SM", "TfNSW")),
])
def test_reviewed_query_situation_resolves_repayment_type_and_direction(question, expected):
    from gateway.native_memory import reviewed_query_situation
    memories = [dict(relation_kind="reimbursement", source_party="TfNSW", target_party="SM"),
        dict(relation_kind="reimbursement", source_party="SM", target_party="TfNSW")]
    result = reviewed_query_situation(question, memories)
    assert result["status"] == "complete"
    assert result["fields"] == dict(relation_kind="reimbursement",
        source_party=expected[0], target_party=expected[1])


def test_reviewed_query_situation_refuses_incomplete_or_unrelated_wording():
    from gateway.native_memory import reviewed_query_situation
    situations = [dict(relation_kind="replacement_cover", source_party="TfNSW", target_party="SM"),
        dict(relation_kind="replacement_cover", source_party="SM", target_party="TfNSW")]
    for question in ("Who reimburses whom?", "If Alpha fails, can Beta arrange cover?"):
        assert reviewed_query_situation(question, situations)["status"] == "incomplete"


def test_rgm_reader_chain_proof_selects_whole_condition_and_repayment_from_bound_source():
    from gateway.native_memory import read_rgm_source_evidence
    source=_replacement_chain_source();packet=_rgm_reader_packet();memory=packet["memories"][0]
    memory["content"]=source["text"]
    memory["evidence_reference"].update(end=100+len(source["text"]),text_sha256=hashlib.sha256(source["text"].encode()).hexdigest())
    # Reader proposal is deliberately wrong. The independent clause proof is
    # bound to retrieved source text, not to that proposal or an expected label.
    generate=lambda *a:dict(raw=json.dumps(dict(status="supported",source_id="wrong",answer_quote="Orchid Transit must reimburse Cedar Authority.")))
    result=read_rgm_source_evidence(CHAIN_QUESTION,packet,generate)
    assert result["status"] == "supported"
    # The span ends at the final source word; a trailing line separator is not
    # part of the quotation returned by the existing exact-span validator.
    assert result["answers"][0]["text"] == source["text"].rstrip()
    assert result["parts"][0]["chain_check"]["status"] == "supported"


def test_rgm_reader_binds_complete_quote_and_keeps_missing_part_separate():
    from gateway.native_memory import read_rgm_source_evidence
    packet = _rgm_reader_packet(); calls = []
    def generate(instruction, data, limit):
        calls.append(data)
        value = (dict(status="supported", source_id="corpus/chunk_1", answer_quote=packet["memories"][0]["content"])
            if len(calls) == 1 else dict(status="not_supported",source_id=None,answer_quote=None))
        return dict(raw=json.dumps(value))
    result = read_rgm_source_evidence("Who pays the premiums? What is the policy number?",packet,generate)
    assert result["status"] == "partial"
    assert result["answers"][0]["text"] == packet["memories"][0]["content"]
    assert result["answers"][0]["start"] == 100
    assert result["answers"][0]["end"] == packet["memories"][0]["evidence_reference"]["end"]
    assert result["answers"][1]["text"] is None
    assert all(c["sources"][0]["text"] == packet["memories"][0]["content"] for c in calls)


def test_rgm_reader_uses_short_source_alias_and_rebinds_complete_server_id():
    from gateway.native_memory import read_rgm_source_evidence
    packet = _rgm_reader_packet()
    canonical_id = "rgm-corpus-" + "7daab18e" * 8 + "/chunk_0"
    packet["memories"][0]["id"] = "chunk_0"
    packet["memories"][0]["evidence_reference"].update(
        corpus_id=canonical_id.rsplit("/", 1)[0], chunk_id="chunk_0")

    def generate(instruction, data, limit):
        assert data["sources"][0]["source_id"] == "source_1"
        return dict(raw=json.dumps(dict(status="supported", source_id="source_1",
            answer_quote=packet["memories"][0]["content"])))

    result = read_rgm_source_evidence("Who pays the premiums?", packet, generate)
    assert result["status"] == "supported"
    assert result["answers"][0]["source_id"] == canonical_id
    assert result["parts"][0]["selection"]["reader_source_alias"] == "source_1"


@pytest.mark.parametrize("damage", ["invented_quote", "wrong_source", "changed_source"])
def test_rgm_reader_rejects_unbound_answer_or_changed_source(damage):
    from gateway.native_memory import read_rgm_source_evidence
    packet = _rgm_reader_packet()
    value = dict(status="supported",source_id="corpus/chunk_1",answer_quote=packet["memories"][0]["content"])
    if damage == "invented_quote": value["answer_quote"] = "Authority must pay 42 dollars."
    elif damage == "wrong_source": value["source_id"] = "unselected-source"
    else: packet["memories"][0]["content"] += " forged"
    if damage == "changed_source":
        with pytest.raises(ValueError,match="changed after resolution"):
            read_rgm_source_evidence("Who pays?",packet,lambda *a:pytest.fail("must reject before reader"))
    else:
        result = read_rgm_source_evidence("Who pays?",packet,lambda *a:dict(raw=json.dumps(value)))
        assert result["status"] == "invalid" and result["answers"][0]["text"] is None


@pytest.mark.parametrize("debtor,creditor", [("SM","TfNSW"),("Cedar Authority","Orchid Transit")])
def test_rgm_reader_real_quote_cannot_reverse_requested_repayment(debtor,creditor):
    from gateway.native_memory import read_rgm_source_evidence
    packet = _rgm_reader_packet()
    text = f"{debtor} must reimburse {creditor} on demand."
    memory = packet["memories"][0];memory["content"] = text
    memory["evidence_reference"].update(end=100+len(text),text_sha256=hashlib.sha256(text.encode()).hexdigest())
    generate = lambda *a:dict(raw=json.dumps(dict(status="supported",source_id="corpus/chunk_1",answer_quote=text)))
    wrong = read_rgm_source_evidence(f"Which clause says {creditor} reimburses {debtor}?",packet,generate)
    assert wrong["status"] == "invalid" and wrong["answers"][0]["text"] is None
    assert "direction" in wrong["parts"][0]["selection"]["error"]
    right = read_rgm_source_evidence(f"Which clause says {debtor} reimburses {creditor}?",packet,generate)
    assert right["status"] == "supported" and right["answers"][0]["text"] == text


def test_rgm_reader_answers_no_only_when_complete_cited_clause_proves_exact_reverse_direction():
    from gateway.native_memory import read_rgm_source_evidence
    packet = _rgm_reader_packet()
    clause = _replacement_chain_source()["text"] + "9.6 Records\nOrchid Transit must retain the records."
    memory = packet["memories"][0]; memory["content"] = clause
    memory["evidence_reference"].update(end=100+len(clause), text_sha256=hashlib.sha256(clause.encode()).hexdigest())
    quote = "Cedar Authority must reimburse\nOrchid Transit for such amount on demand."
    generate = lambda *a: dict(raw=json.dumps(dict(status="supported", source_id="corpus/chunk_1", answer_quote=quote)))
    question = ("Under clause 9.5, if Orchid Transit buys cover because Cedar Authority failed, "
        "does Orchid Transit reimburse Cedar Authority?")
    result = read_rgm_source_evidence(question, packet, generate)
    assert result["status"] == "supported"
    assert result["answers"][0]["claim_verdict"] == "no"
    assert result["answers"][0]["text"].startswith("9.5 Evidence of compliance")
    check = result["parts"][0]["selection"]["claim_check"]
    assert check["requested"] == {"repayment_from": "Orchid Transit", "repayment_to": "Cedar Authority"}
    assert check["actual"] == {"repayment_from": "Cedar Authority", "repayment_to": "Orchid Transit"}


@pytest.mark.parametrize("question", [
    "Does Orchid Transit reimburse Cedar Authority?",
    "Under clause 9.5, which clause says Orchid Transit reimburses Cedar Authority?",
])
def test_rgm_reader_does_not_infer_negative_repayment_without_bounded_yes_no_cited_clause(question):
    from gateway.native_memory import read_rgm_source_evidence
    packet = _rgm_reader_packet()
    text = "Cedar Authority must reimburse Orchid Transit on demand."
    memory = packet["memories"][0]; memory["content"] = text
    memory["evidence_reference"].update(end=100+len(text), text_sha256=hashlib.sha256(text.encode()).hexdigest())
    generate = lambda *a: dict(raw=json.dumps(dict(status="supported", source_id="corpus/chunk_1", answer_quote=text)))
    result = read_rgm_source_evidence(question, packet, generate)
    assert result["status"] == "invalid"


def test_rgm_app_renders_verified_reverse_repayment_as_no_with_exact_source(tmp_path):
    from gateway.native_memory import RgmDocumentService
    library, _ = _rgm_project_library(tmp_path)
    def worker(operation, payload):
        if operation == "rgm_embed":
            return dict(vectors={hashlib.sha256(t.encode()).hexdigest(): [1.0] + [0.0]*383 for t in payload["texts"]})
        memory = payload["packet"]["memories"][0]; ref = memory["evidence_reference"]
        return dict(status="supported", parts=[], answers=[dict(question=payload["question"],
            text=memory["content"], source_id=ref["corpus_id"] + "/" + ref["chunk_id"],
            start=ref["start"], end=ref["end"], provenance=ref, claim_verdict="no")])
    try:
        result = RgmDocumentService(worker=worker, model_identity="fixture").answer("p", library,
            "Under clause 1.1, does Rowan notify Orchid?")
        assert result["status"] == "supported"
        assert result["answer"].startswith("No. The cited clause states the opposite repayment direction:\n\n")
        assert result["sources"][0]["text"] in result["answer"]
    finally:
        library.db.close()


def test_native_answer_full_field_comparison_preserves_branch_identity_and_ambiguity():
    import numpy as np
    from gateway.native_memory import identify_exact_native_field
    ids = np.array(["branch-a", "branch-b"])
    field = np.arange(2048, dtype=float).reshape(2, 32, 32) - 1024
    references = [("opaque-1", ids, field), ("opaque-2", ids, -field)]
    assert identify_exact_native_field(ids, field, references)["matches"] == ["opaque-1"]
    assert identify_exact_native_field(ids, field[::-1], references)["status"] == "unrecognized"
    assert identify_exact_native_field(ids, field, references + [("duplicate", ids, field)])["status"] == "ambiguous"


def _native_library_fixture(tmp_path):
    import numpy as np
    from gateway.native_memory import NativeEvidenceLibrary
    from gateway.permanent_library import PermanentLibrary
    library = PermanentLibrary(tmp_path / "library.sqlite3")
    bridge = NativeEvidenceLibrary(library)
    ids = np.array([7, 11])
    field = np.arange(2048, dtype=float).reshape(2, 32, 32) - 1024
    sources = [dict(source_id="source-a", text="A reimburses B.", provenance={"fixture": True}),
               dict(source_id="source-b", text="B reimburses A.", provenance={"fixture": True})]
    references = [("memory-a", ids, field), ("memory-b", ids, -field)]
    receipts = {handle: bridge.register(handle, source, "tree", ids, value)
                for (handle, ids, value), source in zip(references, sources)}
    return library, bridge, references, receipts, sources


def test_native_library_reopens_exact_sources_and_requires_full_positioned_return(tmp_path):
    import numpy as np
    from gateway.native_memory import NativeEvidenceLibrary
    from gateway.permanent_library import PermanentLibrary
    library, _, references, receipts, sources = _native_library_fixture(tmp_path)
    library.db.close()
    library = PermanentLibrary(tmp_path / "library.sqlite3")
    bridge = NativeEvidenceLibrary(library)
    try:
        for (_, ids, field), source in zip(references, sources):
            result = bridge.recall(ids, field, references, tree_state="tree", expected_bindings=receipts)
            assert result["sources"] == [source]
            assert "supported" not in result
            for wrong in (np.zeros_like(field), field[::-1], field + 0.0001):
                assert bridge.recall(ids, wrong, references, tree_state="tree", expected_bindings=receipts)["sources"] == []
    finally:
        library.db.close()


@pytest.mark.parametrize("mutation", ["source", "resealed_source", "reference", "tree", "missing", "receipt"])
def test_native_library_rejects_broken_or_swapped_provenance(tmp_path, mutation):
    library, bridge, references, receipts, sources = _native_library_fixture(tmp_path)
    _, ids, field = references[0]
    tree = "tree"
    try:
        if mutation in ("source", "resealed_source"):
            record = library.get("memory-a")["record"]
            record["binding"]["source"] = sources[1]
            if mutation == "resealed_source":
                record["receipt_sha256"] = bridge._seal(record["binding"])
            library.db.execute("UPDATE library_records SET record_json=? WHERE record_id=?",
                               (json.dumps(record), "memory-a"))
        elif mutation == "reference":
            references = [("memory-a", ids, -field), references[1]]
        elif mutation == "tree":
            tree = "another-tree"
        elif mutation == "missing":
            library.db.execute("DELETE FROM library_records WHERE record_id='memory-a'")
        else:
            receipts = {"memory-a": receipts["memory-b"], "memory-b": receipts["memory-a"]}
        with pytest.raises(ValueError):
            bridge.recall(ids, field, references, tree_state=tree, expected_bindings=receipts)
    finally:
        library.db.close()


def test_native_library_does_not_overwrite_bindings_or_choose_ambiguous_sources(tmp_path):
    library, bridge, references, receipts, sources = _native_library_fixture(tmp_path)
    _, ids, field = references[0]
    try:
        with pytest.raises(ValueError, match="immutable"):
            bridge.register("memory-a", sources[1], "tree", ids, field)
        receipts["memory-c"] = bridge.register("memory-c", sources[1], "tree", ids, field)
        references.append(("memory-c", ids, field))
        result = bridge.recall(ids, field, references, tree_state="tree", expected_bindings=receipts)
        assert result["status"] == "ambiguous" and result["sources"] == []
    finally:
        library.db.close()


@pytest.mark.parametrize("mutation", ["negation", "citation", "omission", "extra_claim"])
def test_native_answer_final_wording_cannot_add_change_or_lose_approved_claims(mutation):
    from gateway.native_memory import render_native_wording
    approved = _native_answer_profile()["registry"][:1]
    item = dict(source_id=approved[0]["source_id"], text=approved[0]["text"])
    if mutation == "negation": item["text"] = item["text"].replace("must not", "must")
    if mutation == "citation": item["source_id"] = "unapproved"
    if mutation == "extra_claim": item["text"] += " Work can begin immediately."
    value = dict(items=[] if mutation == "omission" else [item])
    with pytest.raises(ValueError): render_native_wording(json.dumps(value), approved)


def test_native_answer_sequence_refuses_unrecognized_memory_without_language_fallback():
    from gateway.native_memory import NativeMemoryService
    calls = []
    def worker(stage, payload):
        calls.append(stage)
        if stage == "access": return dict(candidate_indices=[0, 1, 2], parts=[dict(question=q, candidate_indices=[0, 1, 2]) for q in payload["questions"]])
        if stage == "native": return dict(tree_unchanged=True, checkpoint_state="frozen-tree",
            returns=[dict(decision=dict(status="unrecognized"), source_ids=[])])
        pytest.fail("language generation must not bypass a missing native return")
    service = NativeMemoryService(_native_answer_profile(), worker=worker)
    with pytest.raises(ValueError, match="belong"):
        service.answer("foreign-project", "Who inspects?")
    assert calls == []
    result = service.answer("native-project", "Who inspects?")
    assert result["status"] == "blocked" and result["sources"] == []
    assert calls == ["access", "native"]


def test_native_answer_no_support_is_refusal_with_no_final_wording():
    from gateway.native_memory import NativeMemoryService, NATIVE_REFUSAL
    profile = _native_answer_profile(); calls = []
    def worker(stage, payload):
        calls.append(stage)
        if stage == "access": return dict(candidate_indices=[0, 1, 2], parts=[dict(question=q, candidate_indices=[0, 1, 2]) for q in payload["questions"]])
        if stage == "native": return dict(tree_unchanged=True, checkpoint_state="frozen-tree",
            returns=[dict(decision=dict(status="unique_exact_match"), source_ids=[s["source_id"]]) for s in profile["registry"]])
        return dict(trace=dict(final_llm_calls=0), approved_source_ids=[], wording=None,
            parts=[dict(question=payload["question"], status="not_supported", source_id=None)])
    result = NativeMemoryService(profile, worker=worker).answer("native-project", "What is the missing date?")
    assert result["status"] == "not_supported" and result["answer"] == NATIVE_REFUSAL
    assert calls == ["access", "native", "language"]


def test_native_answer_gateway_status_is_project_bound_without_models(monkeypatch):
    monkeypatch.delenv("TOM_ASSIST_NATIVE_MEMORY_PROFILE", raising=False)
    gateway = types.SimpleNamespace(native_memory_service=None)
    status, result = TomGateway.handle(gateway, "POST", "/document/native-memory/answer", dict(project_id="empty-project", action="status"))
    assert status == 200 and result["ready"] is False
    status, result = TomGateway.handle(gateway, "POST", "/document/native-memory/answer", dict(project_id="empty-project", question="Who pays?", explicit_answer=True))
    assert status == 503



def _empty_roles(request="reimbursement"):
    from gateway.native_memory import EVIDENCE_ROLE_FIELDS
    return dict(request=request, **{k: None for k in EVIDENCE_ROLE_FIELDS})


@pytest.mark.parametrize("text", [
    "Which clause says North Rail reimburses City Works?",
    "Which provision says City Works is reimbursed by North Rail?",
])
def test_question_party_direction_is_preserved_without_candidate_knowledge(text):
    from gateway.native_memory import interpret_native_question
    fields = _empty_roles(); fields["failure_party"] = "City Works"
    result = interpret_native_question(text, fields)
    assert result["fields"]["repayment_from"] == "North Rail"
    assert result["fields"]["repayment_to"] == "City Works"
    assert result["fields"]["failure_party"] == "City Works"
    assert fields["repayment_from"] is None
    assert all(text[g["start"]:g["end"]] == g["value"] for g in result["explicit_relation_guards"])


@pytest.mark.parametrize("text", [
    "North Rail must not reimburse City Works.",
    "Is it not true that North Rail reimburses City Works?",
    "Under clause 23.1, is SM not responsible for deductibles?",
    "North Rail reimburses City Works and City Works repays North Rail.",
])
def test_unresolved_negation_or_conflicting_directions_cannot_become_positive_claim(text):
    from gateway.native_memory import interpret_native_question
    with pytest.raises(ValueError): interpret_native_question(text, _empty_roles())


@pytest.mark.parametrize("party,answer", [("SM", "no"), ("TfNSW", "yes")])
def test_cited_party_question_gets_evidence_bound_yes_or_no(party, answer):
    from gateway.native_memory import select_native_evidence, render_native_verdicts
    question = f"Under clause 23.1, is {party} the party expressly identified as responsible for deductibles?"
    fields = _empty_roles("deductibles"); fields.update(deductible_payer=party, policy_clause="23.1")
    roles = _empty_roles(None); roles.update(deductible_payer="TfNSW", policy_clause="23.1")
    candidate = dict(source_id="source", fields=roles, text="TfNSW bears the deductible under clause 23.1.", source_clause="23.3")
    decision, interpretation = select_native_evidence(question, fields, [candidate])
    assert decision["status"] == "supported" and decision["claim_check"]["answer"] == answer
    assert interpretation["fields"]["deductible_payer"] is None
    part = dict(question=question, **decision)
    source = dict(source_id="source", provenance=dict(clause="23.3", pdf_page=55))
    rendered = render_native_verdicts([part], [source], {"source": roles})
    assert rendered.startswith(answer.capitalize()+".") and "[Clause 23.3, page 55]" in rendered
    part["claim_check"]["answer"] = "no" if answer == "yes" else "yes"
    with pytest.raises(ValueError): render_native_verdicts([part], [source], {"source": roles})


def test_combined_access_uses_both_shortlists_and_recalls_their_union_before_language():
    from gateway.native_memory import NativeMemoryService
    profile = _native_answer_profile(4); calls = []
    def worker(stage, payload):
        calls.append((stage, payload))
        if stage == "plan":
            return dict(raw=json.dumps(dict(questions=["Who pays?", "Who inspects?"])))
        if stage == "access":
            assert payload["questions"] == ["Who pays?", "Who inspects?"]
            return dict(candidate_indices=[0, 1, 2, 3], parts=[dict(question=q, candidate_indices=top) for q, top in zip(payload["questions"], ([0, 1, 2], [2, 3, 1]))])
        if stage == "native":
            assert payload["candidate_indices"] == [0, 1, 2, 3]
            return dict(tree_unchanged=True, checkpoint_state="frozen-tree", returns=[dict(decision=dict(status="unique_exact_match"), source_ids=[s["source_id"]]) for s in profile["registry"]])
        assert payload["parts"] == ["Who pays?", "Who inspects?"]
        return dict(trace={}, approved_source_ids=[], wording=None, parts=[dict(question=q, status="not_supported", source_id=None) for q in payload["parts"]])
    result = NativeMemoryService(profile, worker=worker).answer("native-project", "Explain both who pays and who inspects.")
    assert result["status"] == "not_supported"
    assert [c[0] for c in calls] == ["plan", "access", "native", "language"]


def test_candidate_union_cannot_silently_omit_or_add_an_address():
    from gateway.native_memory import NativeMemoryService
    def worker(stage, payload):
        assert stage == "access"
        return dict(candidate_indices=[0, 1], parts=[dict(question=payload["questions"][0], candidate_indices=[0, 1, 2])])
    result = NativeMemoryService(_native_answer_profile(), worker=worker).answer("native-project", "Who pays?")
    assert result["status"] == "blocked"
    assert "union" in result["trace"]["failure"]["reason"]


def test_negated_failure_condition_is_not_confused_with_negated_repayment():
    from gateway.native_memory import interpret_native_question
    text = "City Works did not show compliance. Which clause makes North Rail repay City Works?"
    roles = _empty_roles(); roles["failure_party"] = "City Works"
    result = interpret_native_question(text, roles)
    assert result["fields"]["repayment_from"] == "North Rail"
    assert result["fields"]["repayment_to"] == "City Works"
    assert result["fields"]["failure_party"] == "City Works"


def test_exact_negated_repayment_supports_only_the_same_named_direction():
    from gateway.native_memory import check_rgm_explicit_negated_repayment_claim
    question = "Does Orchid reimburse Rowan?"
    correct = check_rgm_explicit_negated_repayment_claim(question,
        "Orchid must not reimburse Rowan on demand.")
    assert correct["status"] == "verified" and correct["verdict"] == "no"
    assert check_rgm_explicit_negated_repayment_claim(question,
        "Rowan must not reimburse Orchid on demand.")["status"] == "not_applicable"
    assert check_rgm_explicit_negated_repayment_claim(question,
        "Orchid may reimburse Rowan on demand.")["status"] == "not_applicable"


def _rgm_project_library(tmp_path, name="project"):
    from gateway.permanent_library import PermanentLibrary
    library = PermanentLibrary(tmp_path / (name + ".sqlite3"))
    text = "1.1 Notice\nOrchid must notify Rowan of a leak within two days.\n1.2 Costs\nRowan must pay the repair costs.\n1.3 Records\nKeep the inspection log."
    doc = dict(document_id="doc-1", display_name="Maintenance agreement", content=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(), byte_length=len(text.encode()), media_type="text/plain",
        chunking_version="fixture", embedding_version="fixture", ingested_tick=0, tombstoned_at=None)
    library.retain_document(doc, [], dict(schema_version="fixture", structure_digest="fixture"))
    return library, doc


def _rgm_app_worker(calls, *, damage=None):
    from gateway.native_memory import read_rgm_source_evidence
    def worker(operation, payload):
        calls.append(operation)
        if operation == "rgm_embed":
            return dict(vectors={hashlib.sha256(t.encode()).hexdigest(): [1.0] + [0.0]*383 for t in payload["texts"]})
        def generate(instruction, data, limit):
            source = data["sources"][0]
            if "policy number" in data["question"]:
                value = dict(status="not_supported", source_id=None, answer_quote=None)
            elif "reimburse" in data["question"] and "must not reimburse" in source["text"]:
                value = dict(status="supported", source_id=source["source_id"],
                    answer_quote="Orchid must not reimburse Rowan on demand.")
            else:
                value = dict(status="supported", source_id=source["source_id"],
                    answer_quote="Orchid must notify Rowan of a leak within two days.")
            return dict(raw=json.dumps(value))
        result = read_rgm_source_evidence(payload["question"], payload["packet"], generate)
        if damage == "quote": result["answers"][0]["text"] = "Rowan must notify Orchid."
        if damage == "source": result["answers"][0]["source_id"] = "other-project/source"
        return result
    return worker


def test_rgm_local_copy_is_complete_and_import_isolated():
    from pathlib import Path
    from gateway.native_memory import verify_vendored_rgm
    from gateway.vendor.rgm17d.interface import stm_ltm_retrieval, chat_adapter
    from gateway.vendor.rgm17d.memory.rgm import ReflectionGatedMemory
    assert len(verify_vendored_rgm()) == 64
    for module in (stm_ltm_retrieval, chat_adapter):
        assert Path(module.__file__).is_relative_to(Path(__file__).resolve().parents[1] / "vendor")
    assert ReflectionGatedMemory.__module__.startswith("gateway.vendor.rgm17d.")


def test_rgm_app_path_reopens_cached_document_and_keeps_exact_source(tmp_path):
    from gateway.native_memory import RgmDocumentService
    from gateway.permanent_library import PermanentLibrary
    library, doc = _rgm_project_library(tmp_path)
    calls = []
    service = RgmDocumentService(worker=_rgm_app_worker(calls), model_identity="fixture-model")
    try:
        result = service.answer("project", library, "Who reports leaks to Rowan?")
        assert result["status"] == "supported"
        assert result["purity"]["tree_calls"] == 0
        assert "Orchid must notify Rowan" in result["answer"]
        proof = result["sources"][0]["provenance"]
        assert doc["content"][proof["answer_start"]:proof["answer_end"]] == "Orchid must notify Rowan of a leak within two days."
        assert result["sources"][0]["text"] == doc["content"][proof["start"]:proof["end"]]
        library.db.close()
        library = PermanentLibrary(tmp_path / "project.sqlite3")
        again = service.answer("project", library, "What is the policy number?")
        assert again["status"] == "not_supported"
        assert again["sources"] == []
        assert "not present" in again["answer"]
    finally: library.db.close()


@pytest.mark.parametrize("damage", ["quote", "source"])
def test_rgm_app_path_rejects_changed_quote_or_foreign_source(tmp_path, damage):
    from gateway.native_memory import RgmDocumentService
    library, _ = _rgm_project_library(tmp_path)
    try:
        service = RgmDocumentService(worker=_rgm_app_worker([], damage=damage), model_identity="fixture")
        with pytest.raises(ValueError, match="quotation changed|unretrieved evidence"):
            service.answer("p", library, "Who reports leaks?")
    finally: library.db.close()


def test_rgm_app_withdrawal_during_read_discards_answer(tmp_path):
    from gateway.native_memory import RgmDocumentService
    library, _ = _rgm_project_library(tmp_path)
    inner = _rgm_app_worker([])
    def worker(operation, payload):
        answer = inner(operation, payload)
        if operation == "rgm_read": library.withdraw_document("doc-1", 1)
        return answer
    try:
        with pytest.raises(ValueError, match="collection changed"):
            RgmDocumentService(worker=worker, model_identity="fixture").answer("p", library, "Who reports leaks?")
    finally: library.db.close()


def test_rgm_endpoint_uses_project_library_without_initializing_tree(tmp_path, monkeypatch):
    from gateway.evidence_gateway import EvidenceTomGateway
    from gateway.native_memory import RgmDocumentService
    monkeypatch.setenv("TOM_ASSIST_RGM_DOCUMENT_ANSWERS", "1")
    for name in ("TOM_ASSIST_STRUCTURE_PYTHON", "TOM_ASSIST_MINILM_MODEL", "TOM_ASSIST_RGM_READER_PYTHON"):
        monkeypatch.setenv(name, "/fixture")
    folder = tmp_path / "projects" / "project" / "tom"; folder.mkdir(parents=True)
    library, _ = _rgm_project_library(folder, "library"); library.db.close()
    gateway = object.__new__(EvidenceTomGateway); gateway.data_dir = tmp_path
    gateway.rgm_document_service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture")
    def call(**payload): return gateway.handle("POST", "/document/native-memory/answer", dict(project_id="project", **payload))
    status, ready = call(action="status")
    assert status == 200 and ready["ready"] and ready["engine"] == "rgm"
    assert call(action="answer", question="Who reports leaks?")[0] == 400
    status, result = call(action="answer", explicit_answer=True, question="Who reports leaks?")
    assert status == 200 and result["status"] == "supported"
    authority = dict(action="resolve_source_authority", relation_kind="reimbursement",
        superseding_source_id="SRC-new", superseded_source_ids=["SRC-old"],
        effective_at="2026-09-17T00:00:00Z", reason="Reviewed replacement")
    assert call(**authority)[0] == 400
    assert call(explicit_user_action=True, **authority)[1]["message"] == (
        "source authority must use exact retained RGM source identities")
    status, other = gateway.handle("POST", "/document/native-memory/answer", dict(project_id="other", action="status"))
    assert status == 200 and not other["ready"]
    assert not (tmp_path / "projects" / "other").exists()


def test_rgm_desktop_import_uses_local_chunker_and_never_initializes_tree(tmp_path, monkeypatch):
    from gateway.evidence_gateway import EvidenceTomGateway
    from gateway.native_memory import RgmDocumentService
    from gateway.permanent_library import PermanentLibrary
    monkeypatch.setenv("TOM_ASSIST_RGM_DOCUMENT_ANSWERS", "1")
    gateway = object.__new__(EvidenceTomGateway); gateway.data_dir = tmp_path
    gateway.rgm_document_service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture")
    def call(path, **payload): return gateway.handle("POST", path, dict(project_id="project", **payload))
    assert call("/document/list")[1] == dict(documents=[])
    assert not (tmp_path / "projects").exists()
    text = "1.1 Notice\nOrchid must notify Rowan of a leak within two days.\n1.2 Costs\nRowan pays repair costs."
    data = dict(display_name="Notice terms", content=text, media_type="text/plain")
    assert call("/document/ingest", **data)[0] == 400
    status, result = call("/document/ingest", explicit_user_action=True, **data)
    assert status == 200 and result["tree_calls"] == 0
    doc_id = result["document_id"]
    assert call("/document/ingest", explicit_user_action=True, **data)[1]["duplicate"]
    assert call("/document/get", document_id=doc_id)[1]["content"] == text
    assert call("/document/list")[1]["documents"][0]["chunk_count"] == result["chunk_count"]
    assert call("/memory/diagnostics")[1]["tree_loaded"] is False
    assert not list(tmp_path.rglob("tree_state.json"))
    status, _ = call("/document/withdraw", document_id=doc_id, explicit_user_action=True, tombstoned_at="2026-09-17T00:00:00Z")
    assert status == 200 and call("/document/list")[1]["documents"] == []
    assert call("/document/get", document_id=doc_id)[0] == 400


def _reviewed_tom_profile():
    return dict(python="/fixture/python", native_root="/fixture/native",
        base_checkpoint="/fixture/base.pkl", state_root="/Volumes/Fixture/tom-assist",
        base_checkpoint_sha256="fixture", address_seed=20260916)


def _reviewable_rgm_library(tmp_path):
    from gateway.native_memory import RgmDocumentService
    from gateway.permanent_library import PermanentLibrary
    library = PermanentLibrary(tmp_path / "reviewable.sqlite3")
    text = ("1.1 Replacement cover\nIf Orchid fails to demonstrate compliance, Rowan may obtain "
        "replacement cover. Orchid must reimburse Rowan on demand.\n"
        "1.2 Notice\nOrchid must notify Rowan of a leak within two days.")
    service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture-model")
    result = service.ingest("project", library, dict(explicit_user_action=True,
        display_name="Reviewed agreement", content=text, media_type="text/plain"))
    return library, result


def _reviewed_tom_worker(calls, *, damage=None):
    def worker(operation, payload):
        calls.append((operation, payload))
        if operation == "rgm_tom_learn":
            new_ids = payload["new_memory_ids"]
            source_id = payload["memories"][-1]["source_id"]
            sequence = len(payload["memories"])
            return dict(tree_saved=True,
                tree=dict(sequence=sequence, state_hash=f"state-{sequence}",
                    checkpoint_path=f"/Volumes/Fixture/tom-assist/project/tree-{sequence}.pkl",
                    checkpoint_sha256=f"checkpoint-{sequence}",
                    reference_path=f"/Volumes/Fixture/tom-assist/project/references-{sequence}.npz",
                    reference_sha256=f"references-{sequence}", branch_count=507,
                    terminal_branch_count=254),
                new_memories=[dict(memory_id=memory_id, source_id=source_id,
                    relation_kind=next(m["relation_kind"] for m in payload["memories"]
                        if m["memory_id"] == memory_id),
                    write_keys=[[f"bank-{index}", 0]],
                    reference=dict(field_shape=[254, 32, 32], field_sha256=f"field-{index}"))
                    for index, memory_id in enumerate(new_ids, 1)],
                whole_tree_score=False, all_branch_cell_coordinates_preserved=True)
        if operation == "rgm_tom_recall":
            assert payload["query_situation"] in (
                dict(relation_kind="replacement_cover", source_party="Orchid", target_party="Rowan"),
                dict(relation_kind="reimbursement", source_party="Orchid", target_party="Rowan"),
                dict(relation_kind="before", source_event="notify", target_event="meeting"),
                dict(relation_kind="before", source_event="failure", target_event="substitute_action"),
                dict(relation_kind="before", source_event="substitute_action", target_event="cost_recovery"),
            )
            def key(item):
                endpoints = (("source_event", "target_event") if item["relation_kind"] == "before"
                    else ("source_party", "target_party"))
                return (item["relation_kind"], *(item[name] for name in endpoints))
            match = next(memory for memory in payload["memories"]
                if key(memory) == key(payload["query_situation"]))
            access = set(payload["candidate_source_ids"])
            recalled = list(match.get("source_ids", [match["source_id"]])) if access.intersection(
                match.get("source_ids", [match["source_id"]])) else []
            return dict(status="recalled" if recalled else "no_matching_memory",
                recalled_source_ids=recalled,
                returns=[dict(source_id=source_id, status="exact_native_return",
                    field_shape=[254, 32, 32], field_sha256="field", active_slot_count=381)
                    for source_id in recalled],
                tree_state_hash="state-1", tree_unchanged=True, root_assembly_calls=0,
                whole_tree_score=(damage == "collapsed"),
                all_branch_cell_coordinates_compared=True)
        raise AssertionError(operation)
    return worker


def test_reviewed_tom_legacy_situation_is_read_as_one_replacement_cover_memory():
    from gateway.native_memory import RgmDocumentService
    legacy = dict(source_id="source", text="Orchid Rowan", failure_party="Orchid",
        cover_payer="Rowan", address_index=0, previous_write_keys=[["bank", 1]])
    result = RgmDocumentService._worker_memories(dict(encoded=dict(worker_situation=legacy)))
    assert result == [dict(memory_id="source", source_id="source", text="Orchid Rowan",
        relation_kind="replacement_cover", source_party="Orchid", target_party="Rowan",
        address_index=0, previous_write_keys=[["bank", 1]])]


def test_reviewed_tom_v2_source_memory_is_catalogued_with_its_binding():
    from gateway.native_memory import RgmDocumentService, RGM_TOM_BRIDGE_VERSION_V2
    memory = dict(memory_id="source:reimbursement", source_id="source", text="Orchid Rowan",
        relation_kind="reimbursement", source_party="Orchid", target_party="Rowan",
        address_index=0, previous_write_keys=[["bank", 1]])
    rows = [dict(encoded=dict(version=RGM_TOM_BRIDGE_VERSION_V2,
        worker_memories=[memory]), situation=dict(source_id="source"))]
    assert RgmDocumentService._memory_catalog(rows) == [dict(memory,
        source_ids=["source"])]


def test_reviewed_tom_v3_multi_source_binding_remains_readable():
    from gateway.native_memory import RgmDocumentService, RGM_TOM_BRIDGE_VERSION_V3
    memory = dict(memory_id="memory", source_id="source-a", text="Orchid Rowan",
        relation_kind="reimbursement", source_party="Orchid", target_party="Rowan",
        address_index=0, previous_write_keys=[["bank", 1]])
    def binding(source_id):
        return dict(memory_id="memory", source_id=source_id, relation_kind="reimbursement",
            source_party="Orchid", target_party="Rowan")
    rows = [
        dict(encoded=dict(version=RGM_TOM_BRIDGE_VERSION_V3, worker_memories=[memory],
            worker_bindings=[binding("source-a")]), situation=dict(source_id="source-a")),
        dict(encoded=dict(version=RGM_TOM_BRIDGE_VERSION_V3, worker_memories=[],
            worker_bindings=[binding("source-b")]), situation=dict(source_id="source-b")),
    ]
    assert RgmDocumentService._memory_catalog(rows) == [dict(memory,
        source_ids=["source-a", "source-b"])]


def test_reviewed_rgm_situation_is_persisted_taught_and_used_during_answer(tmp_path):
    from gateway.native_memory import RgmDocumentService, RGM_TOM_SITUATION_PREFIX
    library, ingested = _reviewable_rgm_library(tmp_path)
    calls = []
    service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture-model",
        tom_worker=_reviewed_tom_worker(calls), tom_profile=_reviewed_tom_profile())
    roles = dict(failure_party="Orchid", cover_payer="Rowan",
        repayment_from="Orchid", repayment_to="Rowan", repayment_when="on demand")
    payload = dict(explicit_user_action=True, document_id=ingested["document_id"],
        chunk_index=0, roles=roles)
    try:
        with pytest.raises(ValueError, match="explicit reviewed"):
            service.learn_situation("project", library, dict(payload, explicit_user_action=False))
        learned = service.learn_situation("project", library, payload)
        assert learned["status"] == "learned" and not learned["duplicate"]
        assert learned["write_count"] == 2
        rows = library.records_with_prefix(RGM_TOM_SITUATION_PREFIX)
        assert len(rows) == 1 and rows[0]["content_hash"] == hashlib.sha256(rows[0]["content"].encode()).hexdigest()
        assert service.learn_situation("project", library, payload)["duplicate"]
        question = "If Orchid fails to demonstrate compliance, can Rowan obtain replacement cover?"
        result = service.answer("project", library, question)
        assert result["status"] == "supported" and result["engine"] == "rgm+tom"
        assert result["purity"]["tree_calls"] == 1
        trace = result["trace"]["retrieval"]["reviewed_tom_memory"]
        assert trace["status"] == "recalled" and trace["whole_tree_score"] is False
        assert trace["all_branch_cell_coordinates_compared"] is True
        assert trace["evidence_scope"]["mode"] == "reviewed_tom_sources"
        repayment = service.answer("project", library, "Does Orchid reimburse Rowan?")
        repayment_trace = repayment["trace"]["retrieval"]["reviewed_tom_memory"]
        assert repayment_trace["status"] == "recalled"
        assert repayment["purity"]["tree_calls"] == 1
        generic = service.answer("project", library, "Who reports leaks to Rowan?")
        assert generic["status"] == "supported" and generic["engine"] == "rgm"
        generic_trace = generic["trace"]["retrieval"]["reviewed_tom_memory"]
        assert generic_trace["status"] == "no_query_structure"
        assert generic["purity"]["tree_calls"] == 0
        assert [call[0] for call in calls] == ["rgm_tom_learn", "rgm_tom_recall", "rgm_tom_recall"]
    finally:
        library.db.close()


def test_multiple_rgm_sources_bind_to_one_tom_relationship_without_second_tree_write(tmp_path):
    from gateway.native_memory import RgmDocumentService
    library, first = _reviewable_rgm_library(tmp_path)
    calls = []
    service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture-model",
        tom_worker=_reviewed_tom_worker(calls), tom_profile=_reviewed_tom_profile())
    roles = dict(failure_party="Orchid", cover_payer="Rowan",
        repayment_from="Orchid", repayment_to="Rowan", repayment_when="on demand")
    try:
        initial = service.learn_situation("project", library, dict(explicit_user_action=True,
            document_id=first["document_id"], chunk_index=0, roles=roles))
        assert initial["write_count"] == 2
        second_text = ("1.1 Confirmation\nThe project email confirms that if Orchid fails to demonstrate "
            "compliance, Rowan may obtain replacement cover. Orchid must reimburse Rowan on demand.\n"
            "1.2 Notice\nOrchid must notify Rowan of a leak within two days.")
        second = service.ingest("project", library, dict(explicit_user_action=True,
            display_name="Confirmation email", content=second_text, media_type="text/plain"))
        bound = service.learn_situation("project", library, dict(explicit_user_action=True,
            document_id=second["document_id"], chunk_index=0, roles=roles))
        assert bound["write_count"] == 0
        assert bound["bound_existing_relationships"] == 2
        status = service.structural_status("project", library)
        assert status["learned_situations"] == 2
        assert status["learned_relationship_memories"] == 2

        result = service.answer("project", library,
            "If Orchid fails to demonstrate compliance, can Rowan obtain replacement cover?")
        trace = result["trace"]["retrieval"]["reviewed_tom_memory"]
        assert trace["status"] == "recalled"
        assert trace["evidence_scope"]["selected_count"] == 2
        assert result["purity"]["tree_calls"] == 1
        assert [call[0] for call in calls] == ["rgm_tom_learn", "rgm_tom_recall"]
        recall_payload = calls[-1][1]
        assert len(recall_payload["memories"]) == 2
        assert all(len(memory["source_ids"]) == 2 for memory in recall_payload["memories"])

        conflict_text = ("1.1 Amendment\nIf Orchid fails to demonstrate compliance, Rowan may obtain "
            "replacement cover. Orchid must not reimburse Rowan on demand.\n"
            "1.2 Notice\nOrchid must notify Rowan of a leak within two days.")
        conflict = service.ingest("project", library, dict(explicit_user_action=True,
            display_name="Conflicting amendment", content=conflict_text, media_type="text/plain"))
        with pytest.raises(ValueError, match="explicitly negates reimbursement"):
            service.learn_situation("project", library, dict(explicit_user_action=True,
                document_id=conflict["document_id"], chunk_index=0, roles=roles))

        blocked = service.answer("project", library, "Does Orchid reimburse Rowan?")
        blocked_trace = blocked["trace"]["retrieval"]["reviewed_tom_memory"]
        assert blocked["status"] == "ambiguous"
        assert len(blocked["sources"]) == 3
        assert "must reimburse Rowan" in blocked["answer"]
        assert "must not reimburse Rowan" in blocked["answer"]
        assert blocked["purity"]["tree_calls"] == 0
        assert blocked["trace"]["reading"] == dict(status="ambiguous",
            method="unresolved_source_conflict_presented", model_calls=0, answers=[], parts=[])
        assert blocked_trace["status"] == "source_authority_unresolved"
        assert blocked_trace["evidence_scope"]["mode"] == "all_conflicting_sources"
        assert blocked_trace["evidence_scope"]["selected_count"] == 3
        assert set(blocked_trace["evidence_scope"]["source_ids"]) == {
            source["source_id"] for source in blocked["sources"]}
        assert [call[0] for call in calls] == ["rgm_tom_learn", "rgm_tom_recall"]

        review = blocked["authority_review"]
        assert review["relation_kind"] == "reimbursement"
        assert {row["source_id"] for row in review["current_sources"]} == {
            initial["source_id"], bound["source_id"]}
        conflict_source_id = review["conflict_sources"][0]["source_id"]
        authority = service.resolve_source_authority("project", library, dict(
            explicit_user_action=True, relation_kind="reimbursement",
            superseding_source_id=conflict_source_id,
            superseded_source_ids=[initial["source_id"]],
            effective_at="2026-09-01T00:00:00Z", reason="Reviewed amendment replaces both prior sources"))
        assert authority["link_count"] == 1 and authority["tree_calls"] == 0
        partial = service.answer("project", library, "Does Orchid reimburse Rowan?",
            as_of="2026-09-17T00:00:00Z")
        assert partial["status"] == "ambiguous"
        assert len(partial["sources"]) == 2
        assert partial["trace"]["retrieval"]["reviewed_tom_memory"]["status"] == "source_authority_unresolved"
        completed = service.resolve_source_authority("project", library, dict(
            explicit_user_action=True, relation_kind="reimbursement",
            superseding_source_id=conflict_source_id,
            superseded_source_ids=[bound["source_id"]],
            effective_at="2026-09-01T00:00:00Z", reason="Reviewed amendment replaces both prior sources"))
        assert completed["link_count"] == 1
        duplicate = service.resolve_source_authority("project", library, dict(
            explicit_user_action=True, relation_kind="reimbursement",
            superseding_source_id=conflict_source_id,
            superseded_source_ids=[initial["source_id"], bound["source_id"]],
            effective_at="2026-09-01T00:00:00Z", reason="Reviewed amendment replaces both prior sources"))
        assert duplicate["link_count"] == 0 and duplicate["duplicate_count"] == 2
        with pytest.raises(ValueError, match="cannot form a cycle"):
            service.resolve_source_authority("project", library, dict(
                explicit_user_action=True, relation_kind="reimbursement",
                superseding_source_id=initial["source_id"],
                superseded_source_ids=[conflict_source_id],
                effective_at="2026-09-01T00:00:00Z", reason="Invalid reverse link"))

        not_yet_effective = service.answer("project", library, "Does Orchid reimburse Rowan?",
            as_of="2026-08-31T23:59:59Z")
        assert not_yet_effective["status"] == "ambiguous"
        assert len(not_yet_effective["sources"]) == 3
        assert not_yet_effective["trace"]["retrieval"]["reviewed_tom_memory"]["status"] == (
            "source_authority_unresolved")

        resolved = service.answer("project", library, "Does Orchid reimburse Rowan?",
            as_of="2026-09-17T00:00:00Z")
        resolved_trace = resolved["trace"]["retrieval"]["reviewed_tom_memory"]
        assert resolved["status"] == "supported", resolved["trace"]["reading"]
        assert resolved["purity"]["tree_calls"] == 0
        assert resolved["authority_review"] is None
        assert resolved_trace["status"] == "source_authority_resolved"
        assert resolved_trace["evidence_scope"]["mode"] == "explicit_source_authority"
        assert resolved_trace["authoritative_source_ids"] == [conflict_source_id]
        assert len(resolved["sources"]) == 1
        assert [call[0] for call in calls] == ["rgm_tom_learn", "rgm_tom_recall"]
    finally:
        library.db.close()


def test_reviewed_notice_before_meeting_memory_reopens_every_bound_rgm_source(tmp_path):
    from gateway.native_memory import (RgmDocumentService, bind_recalled_rgm_evidence,
        rgm_candidate_source_id)
    from gateway.permanent_library import PermanentLibrary
    library = PermanentLibrary(tmp_path / "temporal.sqlite3")
    calls = []
    service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture-model",
        tom_worker=_reviewed_tom_worker(calls), tom_profile=_reviewed_tom_profile())
    documents = [
        ("Interface agreement", "11 Dispute process\nFollowing the issue of a written notice, the Executive Group must meet to resolve the issue."),
        ("D&C deed", "31 Claim process\nThe Contractor issues a notice and the parties must meet before the claim response is due."),
    ]
    motif = dict(relation_kind="before", source_event="notify", target_event="meeting")
    try:
        learned = []
        for name, text in documents:
            document = service.ingest("project", library, dict(explicit_user_action=True,
                display_name=name, content=text, media_type="text/plain"))
            learned.append(service.learn_situation("project", library, dict(
                explicit_user_action=True, document_id=document["document_id"], chunk_index=0,
                temporal_motif=motif)))
        assert learned[0]["write_count"] == 1
        assert learned[1]["write_count"] == 0
        assert learned[1]["bound_existing_relationships"] == 1
        assert [call[0] for call in calls] == ["rgm_tom_learn"]
        status = service.structural_status("project", library)
        assert status["learned_structural_memories"] == 1
        assert status["learned_situations"] == 2

        rows = service._situation_rows(library)
        first = rows[0]["situation"]
        proof = first["provenance"]
        packet = dict(memories=[dict(id=proof["chunk_id"], content=proof["source_text"],
            evidence_reference=dict(doc_id=proof["document_id"], chunk_id=proof["chunk_id"],
                corpus_id=proof["corpus_id"], corpus_sha256=proof["corpus_sha256"],
                section_id=proof["section_id"], start=proof["start"], end=proof["end"],
                text_sha256=first["source_text_sha256"], provenance={}))])
        questions = [
            "Which procedures require a written notice, followed by a meeting?",
            "Where does notification happen, then people meet?",
            "Find the sequence notice, meeting, response.",
        ]
        expected_ids = {row["situation"]["source_id"] for row in rows}
        for question in questions:
            returned = service.recall_situations("project", library, packet, question,
                "2026-09-17T00:00:00Z")
            assert returned["status"] == "recalled"
            assert set(returned["recalled_source_ids"]) == expected_ids
            assert returned["whole_tree_score"] is False
            assert returned["all_branch_cell_coordinates_compared"] is True
            expanded = service._restore_recalled_sources(library, packet, returned)
            selected, scope = bind_recalled_rgm_evidence(expanded, returned)
            assert {rgm_candidate_source_id(memory) for memory in selected} == expected_ids
            assert {memory["content"] for memory in selected} == {text for _, text in documents}
            assert scope["selected_count"] == 2
            assert returned["rgm_access_candidate_count"] == 1
            assert returned["linked_source_count"] == 2

        calls_before = len(calls)
        reversed_result = service.recall_situations("project", library, packet,
            "Does the meeting happen before the written notice?", "2026-09-17T00:00:00Z")
        assert reversed_result["status"] == "no_matching_structure"
        assert reversed_result["recalled_source_ids"] == []
        assert len(calls) == calls_before
    finally:
        library.db.close()


@pytest.mark.parametrize("text", [
    ("If SM fails to promptly comply, TfNSW may, at the cost of SM, undertake all actions "
        "necessary to manage the emergency."),
    ("If TfNSW fails to promptly comply, SM may, at the cost of TfNSW, undertake all actions "
        "necessary to manage the emergency."),
    ("TfNSW fails to provide evidence of insurance. SM may effect and maintain that insurance "
        "and pay such premiums. Any amounts paid will be a debt due and TfNSW must reimburse SM."),
    ("SM fails to provide evidence of insurance. TfNSW may effect and maintain that insurance "
        "and pay such premiums. Any amounts paid will be a debt due and SM must reimburse TfNSW."),
    ("The Contractor does not comply. The Principal may employ others to carry out the direction. "
        "The resulting Loss is a debt due from the Contractor."),
    ("The Principal may take any action necessary which the Contractor must take but does not take. "
        "Loss from taking that action or the failure to take it will be a debt due from the Contractor."),
    ("The Contractor is not taking adequate measures. The Principal may take such actions as it "
        "deems necessary and recover its reasonable costs and expenses from the Contractor."),
    ("If the Contractor does not comply, the Principal may have the correction work carried out at "
        "the Contractor's expense, and the cost incurred will be a debt due from the Contractor."),
    ("If the Contractor fails to maintain insurance, the Principal may effect and maintain the "
        "relevant insurances and its costs and expenses will be a debt due from the Contractor."),
    ("If the Contractor fails to pay premiums, the Principal may effect such insurance or pay such "
        "premium and any costs incurred will be a debt due from the Contractor."),
    ("If the Contractor fails to repair the work, the Principal may carry out such work or engage "
        "others to carry out such work and its Loss will be a debt due from the Contractor."),
    ("If the Contractor fails to perform an obligation, the Principal may take such action as may be "
        "necessary to remedy the failure. Its Loss in doing so will be a debt due from the Contractor."),
])
def test_reviewed_failure_step_in_cost_source_forms_are_local(text):
    from gateway.native_memory import FAILURE_STEP_IN_COST_MOTIF, rgm_temporal_motif_receipt
    assert len(rgm_temporal_motif_receipt(
        dict(source_id="SRC-local-chain", text=text), FAILURE_STEP_IN_COST_MOTIF)) == 64


@pytest.mark.parametrize("text", [
    "The Contractor fails to finish on time and liquidated damages become a debt due.",
    "The certifier's cost is a debt due. The Proof Engineer later fails to submit a report.",
    "The Contractor fails to pay an amount. The Principal may perfect a security interest at its expense.",
    ("The Contractor fails to act and the Principal may carry out such work. "
        + "Unrelated contract text. " * 100
        + "A different overpayment is a debt due."),
])
def test_reviewed_failure_step_in_cost_rejects_incomplete_or_distant_phrases(text):
    from gateway.native_memory import FAILURE_STEP_IN_COST_MOTIF, rgm_temporal_motif_receipt
    with pytest.raises(ValueError, match="one local failure"):
        rgm_temporal_motif_receipt(
            dict(source_id="SRC-not-a-chain", text=text), FAILURE_STEP_IN_COST_MOTIF)


def test_reviewed_failure_step_in_cost_preserves_legacy_receipt_offsets():
    import re
    from gateway.native_memory import (FAILURE_STEP_IN_COST_MOTIF, RGM_SITUATION_VERSION,
        native_digest, rgm_temporal_motif_receipt)
    text = ("The Principal may employ others to carry out the direction. The amount of Loss from "
        "the Contractor's failure to comply will be a debt due from the Contractor.")
    patterns = {
        "failure": r"\b(?:fails?\s+to|failure\s+to|does\s+not\s+comply|did\s+not\s+comply)\b",
        "substitute_action": (r"\b(?:undertake\s+all\s+actions|"
            r"employ\s+others\s+to\s+carry\s+out|carry\s+out\s+such\s+work|"
            r"engage\s+others\s+to\s+carry\s+out|step(?:s|ped)?\s+in)\b"),
        "cost_recovery": (r"\b(?:at\s+the\s+cost\s+of|debt\s+due|"
            r"recover(?:s|ed|ing)?\s+(?:the\s+)?cost|reasonable\s+costs?)\b"),
    }
    matches = {name: re.search(pattern, text, re.I) for name, pattern in patterns.items()}
    expected = native_digest(dict(schema=RGM_SITUATION_VERSION, source_id="SRC-existing",
        source_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        temporal_motif=FAILURE_STEP_IN_COST_MOTIF,
        event_offsets={name: [match.start(), match.end()] for name, match in matches.items()}))
    assert rgm_temporal_motif_receipt(
        dict(source_id="SRC-existing", text=text), FAILURE_STEP_IN_COST_MOTIF) == expected


def test_reviewed_failure_step_in_cost_chain_recalls_sources_without_rgm_candidate(tmp_path):
    from gateway.native_memory import (FAILURE_STEP_IN_COST_MOTIF, RgmDocumentService,
        bind_recalled_rgm_evidence, rgm_candidate_source_id)
    from gateway.permanent_library import PermanentLibrary
    library = PermanentLibrary(tmp_path / "step-in-chain.sqlite3")
    calls = []
    service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture-model",
        tom_worker=_reviewed_tom_worker(calls), tom_profile=_reviewed_tom_profile())
    documents = [
        ("M12 emergency work", "14.4 Emergency Work\nIf SM fails to promptly comply, TfNSW may, "
            "at the cost of SM, undertake all actions necessary to manage the emergency."),
        ("D&C quality direction", "13.6 Quality direction\nIf the SCAW Contractor does not comply, "
            "the Principal may employ others to carry out the direction. The resulting Loss is a debt due "
            "from the SCAW Contractor to the Principal."),
    ]
    try:
        learned = []
        for name, text in documents:
            document = service.ingest("project", library, dict(explicit_user_action=True,
                display_name=name, content=text, media_type="text/plain"))
            learned.append(service.learn_situation("project", library, dict(
                explicit_user_action=True, document_id=document["document_id"], chunk_index=0,
                temporal_motif=FAILURE_STEP_IN_COST_MOTIF)))
        assert learned[0]["write_count"] == 2
        assert learned[1]["write_count"] == 0
        assert learned[1]["bound_existing_relationships"] == 2

        packet = dict(memories=[])
        returned = service.recall_situations("project", library, packet,
            "Find procedures where a failure is followed by substitute performance and then a debt.",
            "2026-09-17T00:00:00Z")
        expected_ids = {row["situation"]["source_id"] for row in service._situation_rows(library)}
        assert returned["status"] == "recalled"
        assert set(returned["recalled_source_ids"]) == expected_ids
        assert returned["query_routes"] == 2
        assert returned["whole_tree_score"] is False
        assert returned["all_branch_cell_coordinates_compared"] is True

        expanded = service._restore_recalled_sources(library, packet, returned)
        selected, scope = bind_recalled_rgm_evidence(expanded, returned)
        assert {rgm_candidate_source_id(memory) for memory in selected} == expected_ids
        assert {memory["content"] for memory in selected} == {text for _, text in documents}
        assert scope["selected_count"] == 2
        assert returned["rgm_access_candidate_count"] == 0
        assert returned["linked_source_count"] == 2
        assert [call[0] for call in calls] == [
            "rgm_tom_learn", "rgm_tom_recall", "rgm_tom_recall"]
    finally:
        library.db.close()


def test_live_answer_exposes_every_exact_source_linked_by_temporal_memory(tmp_path, monkeypatch):
    import gateway.native_memory as native_memory
    from gateway.native_memory import RgmDocumentService, read_rgm_source_evidence
    from gateway.permanent_library import PermanentLibrary
    library = PermanentLibrary(tmp_path / "temporal-answer.sqlite3")
    calls = []
    def document_worker(operation, payload):
        if operation == "rgm_embed":
            return dict(vectors={hashlib.sha256(text.encode()).hexdigest(): [1.0] + [0.0] * 383
                for text in payload["texts"]})
        assert operation == "rgm_read"
        assert len(payload["packet"]["memories"]) == 2
        def generate(_instruction, data, _limit):
            source = data["sources"][0]
            return dict(raw=json.dumps(dict(status="supported", source_id=source["source_id"],
                answer_quote=source["text"])))
        return read_rgm_source_evidence(payload["question"], payload["packet"], generate)
    service = RgmDocumentService(worker=document_worker, model_identity="fixture-model",
        tom_worker=_reviewed_tom_worker(calls), tom_profile=_reviewed_tom_profile())
    documents = [
        ("Interface agreement", "11 Dispute process\nFollowing the issue of a written notice, the Executive Group must meet to resolve the issue."),
        ("D&C deed", "31 Claim process\nThe Contractor issues a notice and the parties must meet before the claim response is due."),
    ]
    motif = dict(relation_kind="before", source_event="notify", target_event="meeting")
    try:
        for name, text in documents:
            document = service.ingest("project", library, dict(explicit_user_action=True,
                display_name=name, content=text, media_type="text/plain"))
            service.learn_situation("project", library, dict(explicit_user_action=True,
                document_id=document["document_id"], chunk_index=0, temporal_motif=motif))
        rows = service._situation_rows(library)
        first = rows[0]["situation"]; proof = first["provenance"]
        first_memory = dict(id=proof["chunk_id"], content=proof["source_text"],
            evidence_reference=dict(doc_id=proof["document_id"], chunk_id=proof["chunk_id"],
                corpus_id=proof["corpus_id"], corpus_sha256=proof["corpus_sha256"],
                section_id=proof["section_id"], start=proof["start"], end=proof["end"],
                text_sha256=first["source_text_sha256"], provenance={}))
        titles = {row["situation"]["provenance"]["corpus_id"]:
            row["situation"]["provenance"]["display_name"] for row in rows}
        monkeypatch.setattr(native_memory, "retrieve_rgm_project_documents",
            lambda *_args, **_kwargs: (dict(memories=[first_memory]),
                dict(native={}, candidates=2, titles=titles, tree_calls=0)))
        result = service.answer("project", library,
            "Which procedures require a written notice, followed by a meeting?")
        assert result["status"] == "supported"
        assert len(result["sources"]) == 1
        assert len(result["structural_sources"]) == 2
        assert {source["text"] for source in result["structural_sources"]} == {
            text for _, text in documents}
        trace = result["trace"]["retrieval"]["reviewed_tom_memory"]
        assert trace["status"] == "recalled"
        assert trace["rgm_access_candidate_count"] == 1
        assert trace["linked_source_count"] == 2
        assert trace["evidence_scope"]["selected_count"] == 2
        assert result["purity"]["whole_tree_score"] is False
        assert result["purity"]["complete_distributed_return_compared"] is True

        def refusing_document_worker(operation, payload):
            if operation == "rgm_embed":
                return dict(vectors={hashlib.sha256(text.encode()).hexdigest():
                    [1.0] + [0.0] * 383 for text in payload["texts"]})
            assert operation == "rgm_read"
            return dict(status="not_supported", answers=[dict(
                question=payload["question"], text=None, status="not_supported")], parts=[])
        refusing_service = RgmDocumentService(worker=refusing_document_worker,
            model_identity="fixture-model", tom_worker=_reviewed_tom_worker([]),
            tom_profile=_reviewed_tom_profile())
        refused = refusing_service.answer("project", library,
            "Where does notification happen, then people meet?")
        assert refused["status"] == "partial"
        assert refused["sources"] == []
        assert len(refused["structural_sources"]) == 2
        assert "learned structure" in refused["answer"]
        assert "not present" not in refused["answer"]
        assert refused["trace"]["reading"]["structural_evidence_presentation"] == (
            "reviewed_sources_found_direct_answer_unverified")
    finally:
        library.db.close()


def test_reviewed_relationship_rejects_negated_or_superseding_source():
    from gateway.native_memory import EVIDENCE_ROLE_FIELDS, rgm_role_record_receipt
    roles = dict(request=None, **{key: None for key in EVIDENCE_ROLE_FIELDS})
    roles.update(failure_party="Orchid", cover_payer="Rowan",
        repayment_from="Orchid", repayment_to="Rowan", repayment_when="on demand")
    negated = dict(source_id="source-negated",
        text=("If Orchid fails to demonstrate compliance, Rowan may obtain replacement cover. "
            "Orchid must not reimburse Rowan on demand."))
    with pytest.raises(ValueError, match="explicitly negates reimbursement"):
        rgm_role_record_receipt(negated, roles)

    superseding = dict(source_id="source-superseding",
        text=("This amendment supersedes clause 1.1. If Orchid fails to demonstrate compliance, "
            "Rowan may obtain replacement cover. Orchid must reimburse Rowan on demand."))
    with pytest.raises(ValueError, match="authority or supersession"):
        rgm_role_record_receipt(superseding, roles)


def test_reviewed_tom_return_binds_reader_to_its_exact_rgm_source():
    from gateway.native_memory import bind_recalled_rgm_evidence, rgm_candidate_source_id
    def memory(doc_id, start, end):
        return dict(id=f"chunk-{start}", content="source", evidence_reference=dict(
            doc_id=doc_id, start=start, end=end))
    wrong = memory("document", 0, 10)
    correct = memory("document", 10, 20)
    correct_id = rgm_candidate_source_id(correct)
    selected, scope = bind_recalled_rgm_evidence(dict(memories=[wrong, correct]),
        dict(status="recalled", recalled_source_ids=[correct_id]))
    assert selected == [correct]
    assert scope == dict(mode="reviewed_tom_sources", source_ids=[correct_id],
        candidate_count=2, selected_count=1)


def test_rgm_reader_keeps_all_candidates_when_tom_returns_no_memory():
    from gateway.native_memory import bind_recalled_rgm_evidence
    memories = [dict(id="one"), dict(id="two")]
    selected, scope = bind_recalled_rgm_evidence(dict(memories=memories),
        dict(status="no_candidate_situation", recalled_source_ids=[]))
    assert selected == memories
    assert scope == dict(mode="all_rgm_candidates", source_ids=[], candidate_count=2)


def test_reviewed_rgm_situation_refuses_changed_roles_or_collapsed_recall(tmp_path):
    from gateway.native_memory import RgmDocumentService
    library, ingested = _reviewable_rgm_library(tmp_path)
    calls = []
    service = RgmDocumentService(worker=_rgm_app_worker([]), model_identity="fixture-model",
        tom_worker=_reviewed_tom_worker(calls, damage="collapsed"), tom_profile=_reviewed_tom_profile())
    payload = dict(explicit_user_action=True, document_id=ingested["document_id"], chunk_index=0,
        roles=dict(failure_party="Orchid", cover_payer="Rowan"))
    try:
        service.learn_situation("project", library, payload)
        with pytest.raises(ValueError, match="different reviewed relationship"):
            service.learn_situation("project", library, dict(payload,
                roles=dict(failure_party="Rowan", cover_payer="Orchid")))
        with pytest.raises(ValueError, match="preserve the distributed response"):
            service.answer("project", library,
                "If Orchid fails to demonstrate compliance, can Rowan obtain replacement cover?")
    finally:
        library.db.close()

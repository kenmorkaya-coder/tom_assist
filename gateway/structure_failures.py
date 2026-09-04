"""Closed, bounded failure vocabulary for the local structural parser chain."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping


FAILURE_TAXONOMY_VERSION = "tom-assist-structure-failures/1.1"
MAX_FAILURE_DETAIL_CHARACTERS = 240
UNCLASSIFIED = "unclassified"


@dataclass(frozen=True)
class FailureDefinition:
    code: str
    stage: str
    pattern: str
    example: str
    source: str


# Each entry corresponds to an explicit raise family in the parse/evaluation
# chain. Dynamic indices and values are detail; the category remains stable.
FAILURE_DEFINITIONS = (
    FailureDefinition("config.command", "provider_config", r"worker command is required", "structure worker command is required", "structure_provider.StructureWorkerClient"),
    FailureDefinition("config.missing", "provider_config", r"worker is not configured", "local structure worker is not configured: X", "structure_provider.from_environment"),
    FailureDefinition("dependency.missing", "provider_config", r"must be an existing absolute path", "TOM_MODEL must be an existing absolute path", "structure_provider.from_environment"),
    FailureDefinition("timeout.invalid", "provider_config", r"timeout.*(?:numeric|\[30,1800\])", "structure worker timeout must be numeric", "structure_provider.from_environment"),
    FailureDefinition("worker.spawn", "provider_transport", r"unable to start local structure worker", "unable to start local structure worker", "structure_provider._start"),
    FailureDefinition("worker.pipe", "provider_transport", r"worker has no pipes", "local structure worker has no pipes", "structure_provider.analyze"),
    FailureDefinition("worker.write", "provider_transport", r"stopped before accepting input", "local structure worker stopped before accepting input", "structure_provider.analyze"),
    FailureDefinition("worker.timeout", "provider_transport", r"worker timed out", "local structure worker timed out", "structure_provider.analyze"),
    FailureDefinition("worker.eof", "provider_transport", r"worker ended unexpectedly", "local structure worker ended unexpectedly (1)", "structure_provider.analyze"),
    FailureDefinition("worker.response_json", "provider_transport", r"worker returned invalid JSON", "local structure worker returned invalid JSON", "structure_provider.analyze"),
    FailureDefinition("worker.response_protocol", "provider_transport", r"worker protocol mismatch", "local structure worker protocol mismatch", "structure_provider.analyze"),
    FailureDefinition("worker.response_id", "provider_transport", r"worker response ID mismatch", "local structure worker response ID mismatch", "structure_provider.analyze"),
    FailureDefinition("worker.error_shape", "provider_transport", r"worker error shape mismatch", "local structure worker error shape mismatch", "structure_provider.analyze"),
    FailureDefinition("worker.response_shape", "provider_transport", r"worker response shape mismatch", "local structure worker response shape mismatch", "structure_provider.analyze"),
    FailureDefinition("glossary.provenance", "provider_transport", r"glossary hash mismatch", "local structure worker glossary hash mismatch", "structure_provider.analyze"),
    FailureDefinition("request.json", "worker_request", r"Expecting .*|JSON.*decode", "Expecting property name enclosed in double quotes", "structure_worker.json.loads"),
    FailureDefinition("request.shape", "worker_request", r"request shape mismatch", "worker request shape mismatch", "structure_worker.request"),
    FailureDefinition("request.protocol", "worker_request", r"protocol mismatch", "worker protocol mismatch", "structure_worker.request"),
    FailureDefinition("source.invalid", "worker_request", r"source text must contain 1\.\.48000 characters", "source text must contain 1..48000 characters", "structure_worker.request"),
    FailureDefinition("glossary.invalid", "worker_request", r"declared glossary|document glossary|project glossary|glossary term|glossary source|glossary content", "project glossary fields mismatch", "project_glossary.validate_glossary"),
    FailureDefinition("chunk.source_required", "chunk_plan", r"source text is required for chunking", "source text is required for chunking", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.source_limit", "chunk_plan", r"source text exceeds .* characters", "source text exceeds 48000 characters", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.window", "chunk_plan", r"max_tokens must be", "max_tokens must be in [8,256]", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.overlap", "chunk_plan", r"overlap_tokens must be", "overlap_tokens must be positive and below half the window", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.boundary", "chunk_plan", r"min_boundary_tokens is invalid", "min_boundary_tokens is invalid", "semantic_chunks.build_token_chunks"),
    FailureDefinition("token_offset.shape", "chunk_plan", r"token offset .* must contain start/end", "token offset 0 must contain start/end", "semantic_chunks.build_token_chunks"),
    FailureDefinition("token_offset.type", "chunk_plan", r"token offset .* must contain integers", "token offset 0 must contain integers", "semantic_chunks.build_token_chunks"),
    FailureDefinition("token_offset.order", "chunk_plan", r"token offset .* invalid or unordered", "token offset 0 is invalid or unordered", "semantic_chunks.build_token_chunks"),
    FailureDefinition("token_offset.empty", "chunk_plan", r"tokenizer returned no source offsets", "tokenizer returned no source offsets", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.overlap_bridge", "chunk_plan", r"chunk plan lost its overlap bridge", "chunk plan lost its overlap bridge", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.no_advance", "chunk_plan", r"chunk plan did not advance", "chunk plan did not advance", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.count_limit", "chunk_plan", r"source requires more than .* chunks", "source requires more than 128 chunks", "semantic_chunks.build_token_chunks"),
    FailureDefinition("chunk.tokenizer", "chunk_plan", r"tokenizer invocation failed", "tokenizer invocation failed", "structure_worker.tokenizer"),
    FailureDefinition("embedding.invoke", "embedding", r"embedding invocation failed", "embedding invocation failed", "structure_worker.embedding"),
    FailureDefinition("embedding.window", "embedding", r"semantic chunk exceeds the MiniLM token window", "a semantic chunk exceeds the MiniLM token window", "structure_worker.embedding"),
    FailureDefinition("embedding.dimension", "embedding", r"embedding model returned .* dimensions", "embedding model returned 12 dimensions", "structure_worker.embedding"),
    FailureDefinition("semantic.source", "semantic_profile", r"source text is required$|source text exceeds", "source text is required", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.model", "semantic_profile", r"semantic profile model is required", "semantic profile model is required", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.revision", "semantic_profile", r"semantic profile revision is required", "semantic profile revision is required", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.chunks", "semantic_profile", r"semantic chunks must be an array|semantic profile must contain", "semantic chunks must be an array", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.chunk_shape", "semantic_profile", r"semantic chunk .* shape mismatch", "semantic chunk 0 shape mismatch", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.offset_type", "semantic_profile", r"semantic chunk .* offsets must be integers", "semantic chunk 0 offsets must be integers", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.offset_range", "semantic_profile", r"semantic chunk .* offsets are invalid", "semantic chunk 0 offsets are invalid", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.start", "semantic_profile", r"semantic chunks must begin", "semantic chunks must begin at source offset zero", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.overlap", "semantic_profile", r"semantic chunks must overlap and advance", "semantic chunks must overlap and advance", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.end", "semantic_profile", r"semantic chunks must cover", "semantic chunks must cover the source ending", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.coverage", "semantic_profile", r"semantic chunk adds no new|semantic chunks do not provide exact", "semantic chunk adds no new source coverage", "semantic_chunks.build_semantic_profile"),
    FailureDefinition("semantic.vector_shape", "semantic_profile", r"must contain 384 values", "semantic chunk 0 must contain 384 values", "semantic_chunks._unit_vector"),
    FailureDefinition("semantic.vector_finite", "semantic_profile", r"values must be finite numbers", "semantic chunk 0 values must be finite numbers", "semantic_chunks._unit_vector"),
    FailureDefinition("semantic.vector_norm", "semantic_profile", r"must be unit normalized", "semantic chunk 0 must be unit normalized, got norm 0", "semantic_chunks._unit_vector"),
    FailureDefinition("semantic.centroid_zero", "semantic_profile", r"collapsed to a zero vector", "passage centroid collapsed to a zero vector", "semantic_chunks._normalize"),
    FailureDefinition("gemma.response_json", "gemma_transport", r"Gemma child returned invalid JSON", "Gemma child returned invalid JSON", "structure_worker.GemmaChild.analyze"),
    FailureDefinition("gemma.pipe", "gemma_transport", r"Gemma child has no pipes", "Gemma child has no pipes", "structure_worker.GemmaChild.analyze"),
    FailureDefinition("gemma.eof", "gemma_transport", r"Gemma child ended unexpectedly", "Gemma child ended unexpectedly (1)", "structure_worker.GemmaChild.analyze"),
    FailureDefinition("gemma.protocol", "gemma_transport", r"Gemma child protocol mismatch", "Gemma child protocol mismatch", "structure_worker.GemmaChild.analyze"),
    FailureDefinition("gemma.response_shape", "gemma_transport", r"Gemma child (?:failure|response) shape mismatch", "Gemma child response shape mismatch", "structure_worker.GemmaChild.analyze"),
    FailureDefinition("model.invoke", "model_invocation", r"model invocation failed", "model invocation failed", "gemma_structure_worker.generate"),
    FailureDefinition("tool.container_mismatch", "tool_parse", r"mismatched containers", "Gemma tool call has mismatched containers", "gemma_structure_worker._balanced_call_object"),
    FailureDefinition("tool.unterminated_string", "tool_parse", r"unterminated string", "Gemma tool call has an unterminated string", "gemma_structure_worker._balanced_call_object"),
    FailureDefinition("tool.incomplete_object", "tool_parse", r"no complete object", "Gemma tool call has no complete object", "gemma_structure_worker._balanced_call_object"),
    FailureDefinition("tool.invalid_structure", "tool_parse", r"invalid structured value", "Gemma fallback contains an invalid structured value", "gemma_structure_worker._gemma4_arguments"),
    FailureDefinition("tool.arguments_shape", "tool_parse", r"tool arguments must be an object", "Gemma tool arguments must be an object", "gemma_structure_worker._gemma4_arguments"),
    FailureDefinition("tool.call_count", "tool_parse", r"exactly one recognizable tool call|call the structure tool exactly once", "Gemma must emit exactly one recognizable tool call", "gemma_structure_worker.parse_generated_tool_call"),
    FailureDefinition("tool.name", "tool_parse", r"called the wrong structure tool", "Gemma called the wrong structure tool", "gemma_structure_worker.main"),
    FailureDefinition("canonical.entity_id", "candidate_canonicalization", r"duplicate or empty entity IDs", "model candidate contains duplicate or empty entity IDs", "structural_analysis.canonicalize_candidate_ids"),
    FailureDefinition("canonical.orientation_endpoint", "candidate_canonicalization", r"model orientation refers to an unknown entity", "model orientation refers to an unknown entity", "structural_analysis.canonicalize_candidate_ids"),
    FailureDefinition("canonical.causal_endpoint", "candidate_canonicalization", r"model causal relation refers to an unknown entity", "model causal relation refers to an unknown entity", "structural_analysis.canonicalize_candidate_ids"),
    FailureDefinition("span.missing_quote", "candidate_canonicalization", r"has no exact evidence quote", "entities[0] has no exact evidence quote", "structural_analysis.canonicalize_candidate_spans"),
    FailureDefinition("span.ambiguous_quote", "candidate_canonicalization", r"evidence quote is missing or ambiguous", "entities[0] evidence quote is missing or ambiguous", "structural_analysis.canonicalize_candidate_spans"),
    FailureDefinition("candidate.source", "candidate_validation", r"source text must contain 1\.\.48000 characters", "source text must contain 1..48000 characters", "structural_analysis.validate_candidate"),
    FailureDefinition("candidate.shape", "candidate_validation", r"candidate (?:must be an object|fields mismatch)", "candidate fields mismatch", "structural_analysis.validate_candidate"),
    FailureDefinition("candidate.version", "candidate_validation", r"schema_version is not supported", "candidate schema_version is not supported", "structural_analysis.validate_candidate"),
    FailureDefinition("candidate.source_digest", "candidate_validation", r"candidate is not bound", "candidate is not bound to the source text", "structural_analysis.validate_candidate"),
    FailureDefinition("entity.container", "candidate_validation", r"entities must be an array", "entities must be an array with at most 64 items", "structural_analysis.validate_candidate"),
    FailureDefinition("entity.shape", "candidate_validation", r"entities\[.*\] (?:must be an object|fields mismatch)", "entities[0] fields mismatch", "structural_analysis.validate_candidate"),
    FailureDefinition("identifier.invalid", "candidate_validation", r"must be a stable lower-case identifier", "entities[0].id must be a stable lower-case identifier", "structural_analysis._identifier"),
    FailureDefinition("entity.duplicate", "candidate_validation", r"duplicate entity id", "duplicate entity id: entity_1", "structural_analysis.validate_candidate"),
    FailureDefinition("entity.kind", "candidate_validation", r"unsupported entity kind", "unsupported entity kind: rule", "structural_analysis.validate_candidate"),
    FailureDefinition("label.type", "candidate_validation", r"\.label must be text", "entities[0].label must be text", "structural_analysis._label"),
    FailureDefinition("label.length", "candidate_validation", r"\.label must contain 1\.\.160", "entities[0].label must contain 1..160 characters", "structural_analysis._label"),
    FailureDefinition("span.shape", "candidate_validation", r"\.evidence (?:must be an object|fields mismatch)", "entities[0].evidence fields mismatch", "structural_analysis._validate_span"),
    FailureDefinition("span.offset_type", "candidate_validation", r"offsets must be integers", "entities[0].evidence offsets must be integers", "structural_analysis._validate_span"),
    FailureDefinition("span.offset_range", "candidate_validation", r"offsets are outside source text", "entities[0].evidence offsets are outside source text", "structural_analysis._validate_span"),
    FailureDefinition("span.not_exact", "candidate_validation", r"quote does not exactly match", "entities[0].evidence quote does not exactly match source text", "structural_analysis._validate_span"),
    FailureDefinition("confidence.type", "candidate_validation", r"confidence must be a number in \[0,1\]", "candidate.confidence must be a number in [0,1]", "structural_analysis._finite_unit"),
    FailureDefinition("confidence.range", "candidate_validation", r"confidence must be finite and in \[0,1\]", "candidate.confidence must be finite and in [0,1]", "structural_analysis._finite_unit"),
    FailureDefinition("orientation.container", "candidate_validation", r"orientations must be an array", "orientations must be an array with at most 64 items", "structural_analysis.validate_candidate"),
    FailureDefinition("orientation.shape", "candidate_validation", r"orientations\[.*\] (?:must be an object|fields mismatch)", "orientations[0] fields mismatch", "structural_analysis.validate_candidate"),
    FailureDefinition("relation.duplicate", "candidate_validation", r"duplicate relation id", "duplicate relation id: relation_1", "structural_analysis.validate_candidate"),
    FailureDefinition("orientation.endpoint", "candidate_validation", r"orientation .* invalid directed endpoints", "orientation r1 has invalid directed endpoints", "structural_analysis.validate_candidate"),
    FailureDefinition("orientation.kind", "candidate_validation", r"orientation .* unsupported kind", "orientation r1 has unsupported kind", "structural_analysis.validate_candidate"),
    FailureDefinition("orientation.polarity", "candidate_validation", r"orientation .* unsupported polarity", "orientation r1 has unsupported polarity", "structural_analysis.validate_candidate"),
    FailureDefinition("orientation.modality", "candidate_validation", r"orientation .* unsupported modality", "orientation r1 has unsupported modality", "structural_analysis.validate_candidate"),
    FailureDefinition("orientation.negated", "candidate_validation", r"orientation .* negated must be boolean", "orientation r1 negated must be boolean", "structural_analysis.validate_candidate"),
    FailureDefinition("causal.container", "candidate_validation", r"causal_relations must be an array", "causal_relations must be an array with at most 64 items", "structural_analysis.validate_candidate"),
    FailureDefinition("causal.shape", "candidate_validation", r"causal_relations\[.*\] (?:must be an object|fields mismatch)", "causal_relations[0] fields mismatch", "structural_analysis.validate_candidate"),
    FailureDefinition("causal.endpoint", "candidate_validation", r"causal relation .* invalid cause-to-effect endpoints", "causal relation r1 has invalid cause-to-effect endpoints", "structural_analysis.validate_candidate"),
    FailureDefinition("causal.kind", "candidate_validation", r"causal relation .* unsupported kind", "causal relation r1 has unsupported kind", "structural_analysis.validate_candidate"),
    FailureDefinition("causal.modality", "candidate_validation", r"causal relation .* unsupported modality", "causal relation r1 has unsupported modality", "structural_analysis.validate_candidate"),
    FailureDefinition("causal.negated", "candidate_validation", r"causal relation .* negated must be boolean", "causal relation r1 negated must be boolean", "structural_analysis.validate_candidate"),
    FailureDefinition("signals.shape", "candidate_validation", r"signals (?:must be an object|fields mismatch)", "signals fields mismatch", "structural_analysis.validate_candidate"),
    FailureDefinition("signal.container", "candidate_validation", r"signals\..* must have at most", "signals.threat must have at most 32 items", "structural_analysis.validate_candidate"),
    FailureDefinition("signal.shape", "candidate_validation", r"signals\..*\[.*\] (?:must be an object|fields mismatch)", "signals.threat[0] fields mismatch", "structural_analysis.validate_candidate"),
    FailureDefinition("unknown_fields.shape", "candidate_validation", r"unknown_fields must be a duplicate-free array", "unknown_fields must be a duplicate-free array", "structural_analysis.validate_candidate"),
    FailureDefinition("unknown_fields.vocabulary", "candidate_validation", r"unknown_fields contains an unsupported field", "unknown_fields contains an unsupported field", "structural_analysis.validate_candidate"),
    FailureDefinition("semantic.validate_shape", "merge", r"semantic profile fields mismatch", "semantic profile fields mismatch", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_version", "merge", r"semantic profile version is not supported", "semantic profile version is not supported", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_embedding", "merge", r"semantic embedding version is not supported", "semantic embedding version is not supported", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_chunking", "merge", r"semantic chunking version is not supported", "semantic chunking version is not supported", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_dimension", "merge", r"semantic profile dimension is not supported", "semantic profile dimension is not supported", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_chunks", "merge", r"semantic profile chunks must be an array", "semantic profile chunks must be an array", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_chunk_object", "merge", r"semantic chunk .* must be an object", "semantic chunk 0 must be an object", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_chunk_shape", "merge", r"semantic chunk .* fields mismatch", "semantic chunk 0 fields mismatch", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_chunk_index", "merge", r"semantic chunk indices must be contiguous", "semantic chunk indices must be contiguous", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_offset_type", "merge", r"semantic chunk offsets must be integers", "semantic chunk offsets must be integers", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_offset_range", "merge", r"semantic chunk offsets are invalid", "semantic chunk offsets are invalid", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_span_binding", "merge", r"semantic chunk is not bound to its source span", "semantic chunk is not bound to its source span", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_rebuild", "merge", r"semantic profile rebuild failed", "semantic profile rebuild failed", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_passage_vector", "merge", r"semantic passage vector is invalid", "semantic passage vector is invalid", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("semantic.validate_replay", "merge", r"semantic passage vector does not replay exactly", "semantic passage vector does not replay exactly", "semantic_chunks.validate_semantic_profile"),
    FailureDefinition("merge.profile_chunks", "merge", r"semantic profile has no chunks", "semantic profile has no chunks", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.candidate_count", "merge", r"one structural candidate is required", "one structural candidate is required per semantic chunk", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.candidate_shape", "merge", r"chunk candidate .* fields mismatch", "chunk candidate 0 fields mismatch", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.chunk_index", "merge", r"chunk candidate indices must be contiguous", "chunk candidate indices must be contiguous", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.candidate_validation", "merge", r"chunk candidate .* validation failed", "chunk candidate 0 validation failed", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.entity_limit", "merge", r"merged candidate exceeds the entity limit", "merged candidate exceeds the entity limit", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.orientation_limit", "merge", r"merged candidate exceeds the orientation limit", "merged candidate exceeds the orientation limit", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.causal_limit", "merge", r"merged candidate exceeds the causal-relation limit", "merged candidate exceeds the causal-relation limit", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("merge.signal_limit", "merge", r"merged candidate exceeds (?:rules|contradictions|inferences|sequences|memory_references|future_references|completions|rejections) limit", "merged candidate exceeds rules limit", "structural_analysis.merge_chunk_candidates"),
    FailureDefinition("parser_model.shape", "analysis", r"parser_model fields mismatch", "parser_model fields mismatch", "structural_analysis.validate_parser_model"),
    FailureDefinition("parser_model.version", "analysis", r"parser model version is not supported", "parser model version is not supported", "structural_analysis.validate_parser_model"),
    FailureDefinition("parser_model.value", "analysis", r"parser_model\..* must contain", "parser_model.model must contain 1..256 characters", "structural_analysis.validate_parser_model"),
    FailureDefinition("parser_model.glossary_hash", "analysis", r"parser_model\.glossary_sha256", "parser_model.glossary_sha256 is invalid", "structural_analysis.validate_parser_model"),
    FailureDefinition("parser_model.unexpected_glossary", "analysis", r"only the glossary parser", "only the glossary parser version may carry a glossary hash", "structural_analysis.validate_parser_model"),
    FailureDefinition("evaluation.case_descriptor", "evaluation", r"frozen case descriptor digest mismatch", "frozen case descriptor digest mismatch", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.input_hash", "evaluation", r"frozen input changed", "frozen input changed: case.json", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.identity", "evaluation", r"frozen identity changed", "frozen identity changed: case.json", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.source_hash", "evaluation", r"frozen source changed", "frozen source changed: case.json", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.native_state", "evaluation", r"native state objects differ", "native state objects differ from input: case.json", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.glossary_empty", "evaluation", r"native project produced an empty glossary", "native project produced an empty glossary: case.json", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.budget_plan", "evaluation", r"frozen generation budget does not match", "frozen generation budget does not match the case plan", "wp40_runner.load_cases"),
    FailureDefinition("evaluation.worker_start", "evaluation", r"could not start the persistent local worker", "case off could not start the persistent local worker", "wp40_runner._observation"),
    FailureDefinition("evaluation.chunk_plan", "evaluation", r"changed its frozen chunk plan", "case off changed its frozen chunk plan", "wp40_runner._observation"),
    FailureDefinition("evaluation.budget", "evaluation", r"generation budget exceeded", "local Gemma generation budget exceeded", "wp40_runner.run"),
    FailureDefinition("evaluation.output_exists", "evaluation", r"output already exists", "output already exists: path", "wp40_runner.run"),
    FailureDefinition("evaluation.model_revision", "evaluation", r"local model revision mismatch", "local model revision mismatch: values", "wp40_runner.run"),
)


_BY_CODE = {item.code: item for item in FAILURE_DEFINITIONS}
if len(_BY_CODE) != len(FAILURE_DEFINITIONS):
    raise RuntimeError("failure taxonomy contains duplicate category codes")


def bounded_detail(value: Any) -> str:
    """Normalize detail and retain both ends when it must be shortened."""
    text = " ".join(str(value).split()) or "no detail supplied"
    if len(text) <= MAX_FAILURE_DETAIL_CHARACTERS:
        return text
    marker = " …[bounded]… "
    left = (MAX_FAILURE_DETAIL_CHARACTERS - len(marker)) * 2 // 3
    right = MAX_FAILURE_DETAIL_CHARACTERS - len(marker) - left
    return text[:left] + marker + text[-right:]


def record_for_code(
    code: str,
    detail: Any,
    *,
    chunk_index: int | None = None,
    attempt_ordinal: int | None = None,
) -> dict[str, Any]:
    if code != UNCLASSIFIED and code not in _BY_CODE:
        raise ValueError(f"unknown failure category: {code}")
    return {
        "taxonomy_version": FAILURE_TAXONOMY_VERSION,
        "category": code,
        "detail": bounded_detail(detail),
        "chunk_index": chunk_index,
        "attempt_ordinal": attempt_ordinal,
    }


class ClassifiedStructureError(RuntimeError):
    def __init__(self, failure: Mapping[str, Any]) -> None:
        self.failure = validate_failure_record(failure)
        super().__init__(
            f"{self.failure['category']}: {self.failure['detail']}"
        )


def classify_failure(
    error: BaseException,
    *,
    stage: str,
    chunk_index: int | None = None,
    attempt_ordinal: int | None = None,
) -> dict[str, Any]:
    if isinstance(error, ClassifiedStructureError):
        inherited = dict(error.failure)
        if chunk_index is not None:
            inherited["chunk_index"] = chunk_index
        if attempt_ordinal is not None:
            inherited["attempt_ordinal"] = attempt_ordinal
        return validate_failure_record(inherited)
    detail = f"{type(error).__name__}: {error}"
    message = str(error)
    for definition in FAILURE_DEFINITIONS:
        if definition.stage == stage and re.search(
            definition.pattern, message, flags=re.IGNORECASE,
        ):
            return record_for_code(
                definition.code, detail,
                chunk_index=chunk_index,
                attempt_ordinal=attempt_ordinal,
            )
    return record_for_code(
        UNCLASSIFIED, detail,
        chunk_index=chunk_index,
        attempt_ordinal=attempt_ordinal,
    )


def validate_failure_record(value: Any) -> dict[str, Any]:
    fields = {
        "taxonomy_version", "category", "detail", "chunk_index",
        "attempt_ordinal",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("failure record fields mismatch")
    if value["taxonomy_version"] != FAILURE_TAXONOMY_VERSION:
        raise ValueError("failure taxonomy version is unsupported")
    category = value["category"]
    if category != UNCLASSIFIED and category not in _BY_CODE:
        raise ValueError("failure category is unsupported")
    detail = value["detail"]
    if not isinstance(detail, str) or not detail or len(detail) > MAX_FAILURE_DETAIL_CHARACTERS:
        raise ValueError("failure detail is invalid or unbounded")
    chunk_index = value["chunk_index"]
    attempt = value["attempt_ordinal"]
    if chunk_index is not None and (type(chunk_index) is not int or chunk_index < 0):
        raise ValueError("failure chunk index is invalid")
    if attempt is not None and (type(attempt) is not int or attempt < 1):
        raise ValueError("failure attempt ordinal is invalid")
    return dict(value)


def taxonomy_summary(failures: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {code: 0 for code in sorted(_BY_CODE)}
    counts[UNCLASSIFIED] = 0
    for value in failures:
        row = validate_failure_record(value)
        counts[row["category"]] += 1
    observed = {code: count for code, count in counts.items() if count}
    return {
        "taxonomy_version": FAILURE_TAXONOMY_VERSION,
        "failure_count": len(failures),
        "category_counts": observed,
        "unclassified_count": counts[UNCLASSIFIED],
        "taxonomy_complete": counts[UNCLASSIFIED] == 0,
        "unclassified_alert": (
            None if counts[UNCLASSIFIED] == 0
            else "UNCLASSIFIED FAILURES PRESENT — TAXONOMY IS NOT COMPLETE"
        ),
    }


def validate_worker_telemetry(value: Any) -> dict[str, Any]:
    fields = {
        "planned_chunks", "attempted_chunks", "successful_chunks",
        "failed_chunk_index", "passage_failed", "chunks", "attempts",
        "failures", "taxonomy",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("worker telemetry fields mismatch")
    planned = value["planned_chunks"]
    attempted = value["attempted_chunks"]
    successful = value["successful_chunks"]
    if any(type(item) is not int or item < 0 for item in (planned, attempted, successful)):
        raise ValueError("worker telemetry counts are invalid")
    if attempted > planned or successful > attempted:
        raise ValueError("worker telemetry counts are inconsistent")
    if type(value["passage_failed"]) is not bool:
        raise ValueError("worker telemetry passage outcome is invalid")
    attempts = value["attempts"]
    failures = value["failures"]
    chunks = value["chunks"]
    if not isinstance(attempts, list) or len(attempts) != attempted:
        raise ValueError("worker telemetry attempts are inconsistent")
    if not isinstance(failures, list):
        raise ValueError("worker telemetry failures are inconsistent")
    if not isinstance(chunks, list) or len(chunks) != successful:
        raise ValueError("worker telemetry successful chunks are inconsistent")
    normalized_failures = [validate_failure_record(item) for item in failures]
    chunk_failures = [
        item for item in normalized_failures if item["chunk_index"] is not None
    ]
    setup_failures = [
        item for item in normalized_failures if item["chunk_index"] is None
    ]
    if len(chunk_failures) != attempted - successful or len(setup_failures) > 1:
        raise ValueError("worker telemetry failures are inconsistent")
    if value["passage_failed"] != bool(normalized_failures):
        raise ValueError("worker telemetry passage outcome is inconsistent")
    for ordinal, item in enumerate(attempts, 1):
        if not isinstance(item, Mapping) or set(item) != {
            "chunk_index", "attempt_ordinal", "outcome", "failure",
        }:
            raise ValueError("worker telemetry attempt fields mismatch")
        if item["chunk_index"] != ordinal - 1 or item["attempt_ordinal"] != ordinal:
            raise ValueError("worker telemetry attempt order is invalid")
        if item["outcome"] not in {"succeeded", "failed"}:
            raise ValueError("worker telemetry attempt outcome is invalid")
        if (item["failure"] is None) != (item["outcome"] == "succeeded"):
            raise ValueError("worker telemetry attempt failure is inconsistent")
        if item["failure"] is not None:
            normalized_attempt_failure = validate_failure_record(item["failure"])
            failure_position = len([
                prior for prior in attempts[:ordinal]
                if prior["outcome"] == "failed"
            ]) - 1
            if normalized_attempt_failure != chunk_failures[failure_position]:
                raise ValueError("worker telemetry attempt failure is inconsistent")
    failed_index = value["failed_chunk_index"]
    expected_failed_index = chunk_failures[0]["chunk_index"] if chunk_failures else None
    if failed_index != expected_failed_index:
        raise ValueError("worker telemetry first failed chunk is inconsistent")
    expected_summary = taxonomy_summary(normalized_failures)
    if value["taxonomy"] != expected_summary:
        raise ValueError("worker telemetry taxonomy summary is inconsistent")
    return {
        **dict(value),
        "failures": normalized_failures,
        "taxonomy": expected_summary,
    }


def failures_from_error(error: BaseException) -> list[dict[str, Any]]:
    telemetry = getattr(error, "telemetry", None)
    if isinstance(telemetry, Mapping) and isinstance(telemetry.get("failures"), list):
        return [validate_failure_record(item) for item in telemetry["failures"]]
    failure = getattr(error, "failure", None)
    if failure is not None:
        return [validate_failure_record(failure)]
    return [classify_failure(error, stage="provider_transport")]


def canonical_taxonomy_json() -> str:
    return json.dumps(
        [item.__dict__ for item in FAILURE_DEFINITIONS],
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )

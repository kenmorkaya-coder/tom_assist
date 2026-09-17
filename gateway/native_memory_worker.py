"""Isolated offline workers for native memory access, recall and evidence-bound language."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import numpy as np

from gateway.native_memory import (
    native_file_hash, identify_exact_native_field, native_question_parts,
    QUESTION_PRECISION_INSTRUCTION, validate_native_roles, select_native_evidence,
    NATIVE_WORDING_INSTRUCTION, NATIVE_PLAN_INSTRUCTION, render_native_wording,
)

def native_memory_worker():
    """One bounded offline worker. The gateway never loads the tree and LLM together."""
    import contextlib
    import gc
    import importlib.util
    import resource
    import sys
    import time
    sys.dont_write_bytecode = True
    request = json.load(sys.stdin); p = request["profile"]; payload = request["payload"]
    operation = request["operation"]; started = time.monotonic()
    write_roots = [Path("/private/tmp").resolve(), Path("/private/var/folders").resolve()]
    if operation == "rgm_tom_learn":
        state_root = Path(p.get("state_root", "")).resolve()
        if not state_root.is_relative_to(Path("/Volumes").resolve()):
            raise ValueError("large reviewed ToM tree states require an external-volume root")
        write_roots.append(state_root)
    def readonly(event, args):
        if event == "socket.connect":
            raise PermissionError("native answer workers are offline")
        if event == "open":
            name, mode, flags = args
            writes = isinstance(mode, str) and any(c in mode for c in "wax+") or isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writes and isinstance(name, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(name)).resolve()
                if str(path) != "/dev/null" and not any(path.is_relative_to(root) for root in write_roots):
                    raise PermissionError("native worker cannot write to projects or owner repositories")
    sys.addaudithook(readonly)
    with contextlib.redirect_stdout(sys.stderr):
        if operation in {"rgm_tom_learn", "rgm_tom_recall"}:
            import re
            import tempfile
            root = Path(p["native_root"]).resolve()
            if Path.cwd().resolve() != root or not re.fullmatch(r"[A-Za-z0-9._-]+", p["project_id"]):
                raise ValueError("reviewed ToM worker origin or project identity is invalid")
            sys.path.insert(0, str(root / "src"))
            from tom_matrix import Stream1Tree
            from tom_matrix.relations.precision_routing import capture_precision_readings, precision_route_from_readings
            from gateway.event_graph_compiler import compile_graph
            from gateway.typed_event_graph import VERSION as graph_version

            def checksum(path):
                with Path(path).open("rb") as handle:
                    return hashlib.file_digest(handle, "sha256").hexdigest()

            def address_fields():
                rng = np.random.default_rng(int(p["address_seed"]))
                def basis():
                    q, r = np.linalg.qr(rng.standard_normal((32, 6)))
                    return q * np.sign(np.diag(r))[None, :]
                left, right = basis(), basis()
                values = np.stack([np.outer(left[:, index], right[:, index]) for index in range(6)])
                if not np.allclose(values.reshape(6, -1) @ values.reshape(6, -1).T,
                                   np.eye(6), atol=1e-14):
                    raise ValueError("reviewed ToM address fields are not orthogonal")
                return values

            def relationship_matrix(failure, cover, text):
                entities = []
                for identifier, party in (("failure_party", failure), ("cover_payer", cover)):
                    start = text.find(party)
                    if not isinstance(party, str) or start < 0:
                        raise ValueError("reviewed relationship party is absent from its exact source")
                    identity = "party:" + hashlib.sha256(" ".join(party.split()).casefold().encode()).hexdigest()[:16]
                    entities.append(dict(id=identifier, name=identity,
                        mentions=[dict(start=start, end=start + len(party), quote=party)]))
                graph = dict(version=graph_version, entities=entities, predicates=[], conditions=[],
                    events=[dict(id="reviewed_failure_to_cover", action="cause",
                        roles=dict(actor=None, object=None, source="failure_party", target="cover_payer",
                            recipient=None, authority=None), modality="assertion", negated=False,
                        condition=None, exception=None, complement=None, revision=None, time=None,
                        evidence=[dict(start=0, end=len(text), quote=text)])], links=[], unresolved=[])
                compiled = compile_graph(graph, text)
                if len(compiled.get("loads", [])) != 1:
                    raise ValueError("reviewed relationship did not compile to one structural field")
                value = np.asarray(compiled["loads"][0]["matrix"])
                if value.shape != (32, 32) or not np.isfinite(value).all():
                    raise ValueError("reviewed relationship produced an invalid 32 by 32 field")
                return value

            def situation_matrix(item):
                return relationship_matrix(item["failure_party"], item["cover_payer"], item["text"])

            situations = payload["situations"]
            if (not isinstance(situations, list) or not 1 <= len(situations) <= 6
                or len({item.get("source_id") for item in situations}) != len(situations)
                or sorted(item.get("address_index") for item in situations) != list(range(len(situations)))):
                raise ValueError("reviewed ToM situations are invalid")
            matrices = {item["source_id"]: situation_matrix(item) for item in situations}
            addresses = address_fields()
            state_dir = (Path(p["state_root"]) / p["project_id"]).resolve()
            if not state_dir.is_relative_to(Path(p["state_root"]).resolve()):
                raise ValueError("reviewed ToM project state escaped its root")
            current = payload.get("current")
            if current is None:
                checkpoint = Path(p["base_checkpoint"])
                if checksum(checkpoint) != p["base_checkpoint_sha256"]:
                    raise ValueError("approved 500-branch ToM fixture changed")
            else:
                checkpoint = Path(current["checkpoint_path"])
                if (not checkpoint.resolve().is_relative_to(state_dir)
                    or checksum(checkpoint) != current["checkpoint_sha256"]):
                    raise ValueError("project ToM checkpoint identity changed")
            tree = Stream1Tree.restore(checkpoint)
            if current is not None and tree.state_hash() != current["state_hash"]:
                raise ValueError("project ToM state changed")

            def capture(item, readings, *, matrix_value=None):
                before = tree.state_hash()
                order = list(readings["order"])
                tips = [branch for branch in order if not readings["children"][branch]]
                value = matrices[item["source_id"]] if matrix_value is None else matrix_value
                path = precision_route_from_readings(value, readings)
                _, returned, selected = tree._terminal_returns(path)
                field = np.stack([returned[branch] for branch in tips])
                capacity = len(next(iter(tree.paired_units.values())).occupied)
                active = np.zeros((len(tips), capacity), dtype=bool)
                keys = set()
                for row, branch in enumerate(tips):
                    active[row, selected[branch]["active"]] = True
                    keys.update((tree.paired_placement[branch], int(slot))
                                for slot in selected[branch]["active"])
                if tree.state_hash() != before or not np.isfinite(field).all():
                    raise ValueError("reviewed ToM read changed state or returned invalid cells")
                return order, tips, field, active, keys

            if operation == "rgm_tom_learn":
                new_source = payload["new_source_id"]
                item = next((row for row in situations if row["source_id"] == new_source), None)
                if item is None or item["address_index"] != len(situations) - 1:
                    raise ValueError("new reviewed situation is not the next bounded address")
                before_updates = {bank: unit.updates.copy() for bank, unit in tree.paired_units.items()}
                before_state = tree.state_hash()
                tree.teaching_enabled = True
                try:
                    tree.observe(matrices[new_source], addresses[item["address_index"]],
                        event_id="rgm-reviewed-" + hashlib.sha256(new_source.encode()).hexdigest()[:20])
                finally:
                    tree.teaching_enabled = False
                write_keys = set()
                for bank, unit in tree.paired_units.items():
                    old = before_updates.get(bank, np.zeros_like(unit.updates))
                    write_keys.update((bank, int(slot)) for slot in np.flatnonzero(unit.updates != old))
                prior = {(bank, int(slot)) for row in situations[:-1]
                    for bank, slot in row.get("previous_write_keys", [])}
                if not write_keys or write_keys & prior or tree.state_hash() == before_state:
                    raise ValueError("reviewed ToM write is empty, overlapping, or unchanged")
                readings = capture_precision_readings(tree)
                captures = []
                for row in situations:
                    order, tips, field, active, keys = capture(row, readings)
                    expected = write_keys if row["source_id"] == new_source else {
                        (bank, int(slot)) for bank, slot in row.get("previous_write_keys", [])}
                    if keys != expected:
                        raise ValueError("reviewed ToM memory no longer opens its exact owned slots")
                    captures.append((field, active))
                state_dir.mkdir(parents=True, exist_ok=True)
                sequence = len(situations)
                saved_checkpoint = state_dir / f"tree-{sequence}.pkl"
                reference_path = state_dir / f"references-{sequence}.npz"
                tree.save(saved_checkpoint)
                temporary = reference_path.with_suffix(".npz.tmp")
                try:
                    with temporary.open("wb") as handle:
                        np.savez_compressed(handle,
                            source_ids=np.asarray([row["source_id"] for row in situations]),
                            branch_ids=np.asarray(order), terminal_branch_ids=np.asarray(tips),
                            fields=np.stack([row[0] for row in captures]),
                            active_slots=np.stack([row[1] for row in captures]))
                    temporary.replace(reference_path)
                finally:
                    temporary.unlink(missing_ok=True)
                tree_record = dict(sequence=sequence, state_hash=tree.state_hash(),
                    checkpoint_path=str(saved_checkpoint), checkpoint_sha256=checksum(saved_checkpoint),
                    reference_path=str(reference_path), reference_sha256=checksum(reference_path),
                    branch_count=len(order), terminal_branch_count=len(tips))
                result = dict(source_id=new_source, tree_saved=True, tree=tree_record,
                    write_keys=sorted([list(key) for key in write_keys]),
                    reference=dict(field_shape=list(captures[-1][0].shape),
                        field_sha256=hashlib.sha256(captures[-1][0].tobytes()).hexdigest()),
                    whole_tree_score=False, all_branch_cell_coordinates_preserved=True,
                    starting_state_hash=before_state, learned_state_hash=tree.state_hash())
            else:
                if current is None:
                    raise ValueError("reviewed ToM recall requires a learned project state")
                query = payload.get("query_situation")
                if (not isinstance(query, dict) or set(query) != {"failure_party", "cover_payer"}
                    or not all(isinstance(query[key], str) and query[key].strip() for key in query)
                    or query["failure_party"] == query["cover_payer"]):
                    raise ValueError("one complete reviewed query relationship is required")
                known_parties = {item[key] for item in situations
                    for key in ("failure_party", "cover_payer")}
                if not set(query.values()) <= known_parties:
                    raise ValueError("query relationship contains an unknown reviewed party")
                query_text = query["failure_party"] + " " + query["cover_payer"]
                query_matrix = relationship_matrix(query["failure_party"], query["cover_payer"], query_text)
                reference_path = Path(current["reference_path"])
                if (not reference_path.resolve().is_relative_to(state_dir)
                    or checksum(reference_path) != current["reference_sha256"]):
                    raise ValueError("project ToM distributed references changed")
                stat = checkpoint.stat()
                before_state = tree.state_hash()
                readings = capture_precision_readings(tree)
                with np.load(reference_path, allow_pickle=False) as archive:
                    source_ids = archive["source_ids"].tolist()
                    if source_ids != [row["source_id"] for row in situations]:
                        raise ValueError("project ToM source order changed")
                    if (archive["branch_ids"].tolist() != list(readings["order"])
                        or archive["terminal_branch_ids"].tolist() != [branch for branch in readings["order"]
                            if not readings["children"][branch]]):
                        raise ValueError("project ToM branch positions changed")
                    _, _, query_field, query_active, query_keys = capture(
                        {"source_id": "__query__"}, readings, matrix_value=query_matrix)
                    recalled = []; returns = []; checks = []
                    for source_id in payload["candidate_source_ids"]:
                        index = source_ids.index(source_id)
                        item = situations[index]
                        expected_keys = {(bank, int(slot)) for bank, slot in item["previous_write_keys"]}
                        exact_field = np.array_equal(query_field, archive["fields"][index])
                        exact_slots = (np.array_equal(query_active, archive["active_slots"][index])
                            and query_keys == expected_keys)
                        checks.append(dict(source_id=source_id,
                            same_complete_branch_cell_field=bool(exact_field),
                            same_complete_native_slot_map=bool(exact_slots)))
                        if exact_field and exact_slots:
                            recalled.append(source_id)
                            returns.append(dict(source_id=source_id, status="exact_native_return",
                                field_shape=list(query_field.shape),
                                field_sha256=hashlib.sha256(query_field.tobytes()).hexdigest(),
                                active_slot_count=len(query_keys)))
                now = checkpoint.stat()
                if tree.state_hash() != before_state or (stat.st_size, stat.st_mtime_ns) != (now.st_size, now.st_mtime_ns):
                    raise ValueError("reviewed ToM recall changed the saved tree")
                result = dict(status="recalled" if recalled else "no_matching_memory",
                    recalled_source_ids=recalled, returns=returns, candidate_checks=checks,
                    tree_state_hash=before_state, tree_unchanged=True, root_assembly_calls=0,
                    whole_tree_score=False, all_branch_cell_coordinates_compared=True,
                    query_routes=1,
                    access_mode="one query-derived reviewed structural field routes once through ToM")
        elif operation == "rgm_extract":
            from gateway.vendor.rgm17d.interface.doc_ingest import read_pdf_file, read_txt_file
            source = Path(payload["source_path"])
            if not source.is_absolute() or not source.is_file() or source.suffix.lower() not in {".pdf", ".txt", ".md"}:
                raise ValueError("select an existing local PDF, text or Markdown file")
            if source.stat().st_size > 100_000_000:
                raise ValueError("file exceeds the experimental 100 MB import limit")
            before = native_file_hash(source)
            text, error = (read_pdf_file if source.suffix.lower() == ".pdf" else read_txt_file)(str(source))
            if error or not text.strip():
                raise ValueError(error or "document has no extractable text")
            if len(text) > 2_000_000 or native_file_hash(source) != before:
                raise ValueError("document is too large or changed during extraction")
            result = dict(content=text, display_name=source.name, media_type="text/plain",
                source_provenance=dict(path=str(source), file_sha256=before, original_suffix=source.suffix.lower()))
        elif operation == "rgm_embed":
            from gateway.semantic_chunks import build_token_chunks, build_semantic_profile
            import torch
            from transformers import AutoTokenizer, AutoModel
            model_path = Path(p["minilm_model"])
            if not model_path.is_absolute() or not model_path.is_dir():
                raise ValueError("local MiniLM snapshot is not configured")
            texts = payload["texts"]
            if not isinstance(texts, list) or not 1 <= len(texts) <= 4097 or any(
                not isinstance(t, str) or not t.strip() or len(t) > 4000 for t in texts):
                raise ValueError("invalid RGM embedding request")
            torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
            tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
            model = AutoModel.from_pretrained(str(model_path), local_files_only=True).eval().to("cpu")
            plans, windows = [], []
            for text in texts:
                offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)["offset_mapping"]
                plan = build_token_chunks(text, offsets, max_tokens=188)
                plans.append(plan)
                windows.extend(text[c["start"]:c["end"]] for c in plan)
            vectors = []
            for start in range(0, len(windows), 16):
                batch = tokenizer(windows[start:start+16], padding=True, truncation=False, return_tensors="pt")
                if int(batch["attention_mask"].sum(dim=1).max()) > 194:
                    raise ValueError("MiniLM window exceeds the frozen bound")
                with torch.inference_mode():
                    hidden = model(**batch).last_hidden_state
                    mask = batch["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                    vectors.extend(torch.nn.functional.normalize(pooled, p=2, dim=1).tolist())
            encoded, cursor = {}, 0
            for text, plan in zip(texts, plans):
                profile = build_semantic_profile(text, [dict(start=c["start"], end=c["end"], values=vectors[cursor+i])
                    for i, c in enumerate(plan)], model="sentence-transformers/all-MiniLM-L6-v2", revision=model_path.name)
                encoded[hashlib.sha256(text.encode()).hexdigest()] = profile["passage_vector"]
                cursor += len(plan)
            result = dict(vectors=encoded, tree_calls=0, truncated_inputs=0)
        elif operation == "rgm_read":
            from gateway.tom_gateway import GemmaInspection
            from gateway.native_memory import read_rgm_source_evidence
            # This reader was measured at 15.04 GiB. Cap its allocation at
            # 17 GiB and require another 2 GiB of currently available memory.
            # The older 22 GiB inspection estimate includes different work.
            exclude = []
            cpu_pid = p.get("concurrent_cpu_pid")
            if cpu_pid is not None:
                import subprocess
                if type(cpu_pid) is not int or cpu_pid <= 1:
                    raise ValueError("invalid isolated CPU test process")
                command = subprocess.check_output(["ps", "-p", str(cpu_pid), "-o", "rss=,command="], text=True)
                loaded = subprocess.check_output(["lsof", "-a", "-p", str(cpu_pid), "-d", "cwd,txt", "-Fn"], text=True)
                if ("tools/native_500_strengthened_cue_reasoning.py" not in command
                    or "n/Users/kenmorkaya/PycharmProjects/tom_matrix_native_stream1\n" not in loaded
                    or "libmlx" in loaded.lower() or int(command.split()[0])*1024 > 4*1024**3):
                    raise ValueError("concurrent job does not match the authorized small CPU tree test")
                exclude = [cpu_pid]
            resources = GemmaInspection.resources(before_load=False, exclude=exclude)
            if resources["estimated_available_bytes"] < 19 * 1024**3:
                resources["blockers"].append("reader requires 17 GiB capped allocation plus 2 GiB reserve")
            if resources["blockers"]:
                raise ValueError("local reader unavailable: " + "; ".join(resources["blockers"]))
            for name, expected in GemmaInspection.MODEL_HASHES.items():
                if native_file_hash(GemmaInspection.MODEL / name) != expected:
                    raise ValueError("reader model changed")
            import mlx.core as mx
            from mlx_lm import load, stream_generate
            from mlx_lm.sample_utils import make_sampler
            mx.set_memory_limit(17 * 1024**3); mx.set_cache_limit(256 * 1024**2)
            mx.random.seed(7); mx.reset_peak_memory()
            model, tokenizer = load(str(GemmaInspection.MODEL))
            def generate(instruction, data, limit):
                prompt = tokenizer.apply_chat_template([dict(role="user", content=instruction + "\nINPUT_JSON:\n" + json.dumps(data))],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False)
                if len(tokenizer.encode(prompt, add_special_tokens=False)) >= 8192:
                    raise ValueError("complete evidence exceeds the reader context; no source was truncated")
                generated = GemmaInspection.collect_extraction(stream_generate(model, tokenizer, prompt=prompt,
                    max_tokens=limit, sampler=make_sampler(temp=0)), tokenizer.eos_token_ids)
                generated["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
                return generated
            result = read_rgm_source_evidence(payload["question"], payload["packet"], generate)
            result["model_peak_bytes"] = mx.get_peak_memory()
            result["resource_check"] = dict(available_bytes=resources["estimated_available_bytes"],
                model_limit_bytes=17*1024**3, reserve_bytes=2*1024**3, verified_concurrent_cpu_pid=cpu_pid)
        elif operation == "access":
            import torch
            from transformers import AutoTokenizer, AutoModel
            torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
            for name, expected in p["minilm_files"].items():
                if native_file_hash(Path(p["minilm_model"]) / name) != expected:
                    raise ValueError("MiniLM model changed")
            if native_file_hash(p["numeric"]["path"]) != p["numeric"]["sha256"]:
                raise ValueError("canonical input fixture changed")
            tokenizer = AutoTokenizer.from_pretrained(p["minilm_model"], local_files_only=True)
            model = AutoModel.from_pretrained(p["minilm_model"], local_files_only=True).eval()
            converter_path = Path(p["native_root"]) / "tools/sentence_matrix_comparison.py"
            if native_file_hash(converter_path) != p["converter_sha256"]:
                raise ValueError("native input converter changed")
            spec = importlib.util.spec_from_file_location("native_converter", converter_path)
            converter = importlib.util.module_from_spec(spec); spec.loader.exec_module(converter)
            questions = payload.get("questions", [payload.get("question")])
            if not isinstance(questions, list) or not 1 <= len(questions) <= 4 or any(not isinstance(q, str) or not q.strip() for q in questions):
                raise ValueError("invalid access questions")
            with np.load(p["numeric"]["path"], allow_pickle=False) as z:
                anchors = z["embeddings"][:len(p["registry"])].copy()
            parts = []; indices = []
            # Preserve the original one-question numerical path, independently
            # for each request. Only the union of memory addresses is new.
            for question in questions:
                tokens = tokenizer([question], padding="max_length", max_length=256, truncation=False, return_tensors="pt")
                if tuple(tokens["input_ids"].shape) != (1, 256):
                    raise ValueError("question exceeds the frozen encoder's token bound")
                with torch.inference_mode():
                    hidden = model(**tokens).last_hidden_state
                    mask = tokens["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                    pooled = (torch.sum(hidden * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)).numpy().copy()
                embedding = converter.norm(pooled)[0]
                scores = embedding @ anchors.T
                top = np.argsort(-scores, kind="stable")[:3].tolist()
                parts.append({"question": question, "candidate_indices": top, "minilm_scores": scores.tolist(),
                    "query_embedding_sha256": hashlib.sha256(embedding.tobytes()).hexdigest(),
                    "tokens": int(tokens["attention_mask"].sum()), "top_k": 3, "truncated": False})
                indices.extend(i for i in top if i not in indices)
            result = {"candidate_indices": indices, "parts": parts, "top_k_per_part": 3}
        elif operation == "native":
            root = Path(p["native_root"])
            if Path.cwd().resolve() != root.resolve() or any(n == "tom_matrix" or n.startswith("tom_matrix.") for n in sys.modules):
                raise ValueError("native worker origin or import boundary violated")
            # A hash-verified frozen package may be retained outside the owner checkout.
            sys.path.insert(0, p.get("native_package_parent", str(root / "src")))
            from tom_matrix import Stream1Tree
            from tom_matrix.core.checkpoint import source_hashes
            from tom_matrix.relations.precision_routing import capture_precision_readings, precision_route_from_readings
            if source_hashes() != p["native_sources"]:
                raise ValueError("native source code changed")
            for item in (p["checkpoint"], p["numeric"], p["references"]):
                if native_file_hash(item["path"]) != item["sha256"]:
                    raise ValueError("frozen native artifact changed")
            checkpoint = Path(p["checkpoint"]["path"]); stat = checkpoint.stat()
            tree = Stream1Tree.restore(checkpoint); before = tree.state_hash()
            if before != p["checkpoint"]["state_hash"]:
                raise ValueError("wrong native tree state")
            readings = capture_precision_readings(tree)
            tips = np.array([b for b in readings["order"] if not readings["children"][b]])
            with np.load(p["numeric"]["path"], allow_pickle=False) as z:
                inputs = z["inputs"][:len(p["registry"])].copy()
            bindings = p["reference_bindings"]; returns = []
            with np.load(p["references"]["path"], allow_pickle=False) as z:
                if not np.array_equal(tips, z["learned_terminal_ids"]):
                    raise ValueError("native branch order changed")
                references = [(h, tips, z[f"learned_fact_{i}_paired_return"]) for h, i in bindings.items()]
                for fact in payload["candidate_indices"]:
                    path = precision_route_from_readings(inputs[fact], readings)
                    _, local, selected = tree._terminal_returns(path)
                    field = np.stack([local[b] for b in tips])
                    decision = identify_exact_native_field(tips, field, references)
                    decision.pop("cell_equal")
                    identities = [p["registry"][bindings[h]]["source_id"] for h in decision["matches"]]
                    returns.append({"decision": decision, "source_ids": identities,
                        "field_shape": list(field.shape), "field_sha256": hashlib.sha256(field.tobytes()).hexdigest(),
                        "reference_fields": [f"learned_fact_{bindings[h]}_paired_return" for h in decision["matches"]],
                        "complete_field_archive": p["references"],
                        "all_branch_cell_coordinates_compared": True,
                        "active_slot_count_display_only": sum(len(selected[b]["active"]) for b in tips)})
                    del path, local, selected, field; gc.collect()
            after = tree.state_hash(); now = checkpoint.stat()
            if after != before or source_hashes() != p["native_sources"] or (stat.st_size, stat.st_mtime_ns) != (now.st_size, now.st_mtime_ns):
                raise ValueError("native recall changed frozen state")
            result = {"returns": returns, "checkpoint_state": before, "tree_unchanged": True,
                "branch_count": len(readings["order"]), "return_branch_count": len(tips),
                "root_assembly_calls": 0, "training_calls": 0, "selector_changed": False}
        elif operation in ("plan", "language"):
            from gateway.tom_gateway import GemmaInspection
            resources = GemmaInspection.resources()
            if resources["blockers"]:
                raise ValueError("local reader unavailable: " + "; ".join(resources["blockers"]))
            for name, expected in p["reader_model_files"].items():
                if native_file_hash(Path(p["reader_model"]) / name) != expected:
                    raise ValueError("reader model changed")
            import mlx.core as mx
            from mlx_lm import load, stream_generate
            from mlx_lm.sample_utils import make_sampler
            mx.set_memory_limit(19 * 1024**3); mx.set_cache_limit(256 * 1024**2)
            mx.random.seed(7); mx.reset_peak_memory()
            model, tokenizer = load(p["reader_model"])
            def generate(instruction, data, limit):
                prompt = tokenizer.apply_chat_template([{"role": "user", "content": instruction + "\nINPUT_JSON:\n" + json.dumps(data)}],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False)
                if len(tokenizer.encode(prompt, add_special_tokens=False)) >= 4096:
                    raise ValueError("language input exceeds the frozen bound")
                generated = GemmaInspection.collect_extraction(stream_generate(model, tokenizer, prompt=prompt,
                    max_tokens=limit, sampler=make_sampler(temp=0)), tokenizer.eos_token_ids)
                generated["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
                return generated
            if operation == "plan":
                result = generate(NATIVE_PLAN_INSTRUCTION, {"question": payload["question"]}, 512)
            else:
                question = payload["question"]
                parts, planning = payload["parts"], payload["planning"]
                sources = [s for identity in payload["source_ids"] for s in p["registry"] if s["source_id"] == identity]
                role_sources = [{"source_id": s["source_id"], "fields": p["source_roles"][s["source_id"]],
                    "text": s["text"], "source_clause": s["provenance"]["clause"]} for s in sources]
                outcomes = []; generations = []; approved_ids = []
                for part in parts:
                    generation = generate(QUESTION_PRECISION_INSTRUCTION, {"kind": "question", "text": part}, 512)
                    fields, offsets = validate_native_roles(generation["raw"], part)
                    decision, interpretation = select_native_evidence(part, fields, role_sources)
                    outcome = {"question": part, "status": decision["status"], "source_id": decision["source_id"]}
                    if "claim_check" in decision:
                        outcome["claim_check"] = decision["claim_check"]
                    if decision["status"] == "supported" and decision["source_id"] not in approved_ids:
                        approved_ids.append(decision["source_id"])
                    outcomes.append(outcome); generations.append({"generation": generation, "fields": fields, "offsets": offsets,
                        "interpretation": interpretation, "decision": decision})
                approved = [next(s for s in sources if s["source_id"] == identity) for identity in approved_ids]
                wording = None
                if approved:
                    wording = generate(NATIVE_WORDING_INSTRUCTION, {"approved_sources": [{"source_id": s["source_id"], "text": s["text"]} for s in approved]}, 2048)
                    render_native_wording(wording["raw"], approved)
                result = {"parts": outcomes, "approved_source_ids": approved_ids, "wording": wording,
                    "trace": {"planning": planning, "evidence": generations, "final_wording": wording,
                        "final_llm_calls": int(bool(approved)), "source_roles_reused_frozen": True,
                        "model_adapter": None, "mlx_peak_bytes": mx.get_peak_memory()}}
            del model, tokenizer; gc.collect(); mx.clear_cache()
        else:
            raise ValueError("unknown native memory stage")
        result["seconds"] = round(time.monotonic() - started, 2)
        result["process_peak_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(result), flush=True)

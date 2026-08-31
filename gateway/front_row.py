"""Product-owned RGM extensions; upstream stays read-only."""
from memory.rgm import ReflectionGatedMemory


class FrontRowMemory(ReflectionGatedMemory):
    def __init__(self, library, capacity=4096):
        super().__init__(capacity=capacity)
        self.library = library
        self.commit_key = None
        self._maintenance = False
        self._serving = set()

    def write_memory(self, record):
        # All write wrappers reach this seam, including committed readmission.
        self.library.assert_twin(record)
        return super().write_memory(record)

    def write(self, item, meta=None):
        if hasattr(item, "content_hash"):
            self.library.assert_twin(item)
            # Preserve pinned checksum deduplication (rgm.py:851-854), without
            # quarantining a second committed use or reinforcing an unused anchor.
            for record in self.state.anchors.values():
                if record.content_hash == item.content_hash:
                    return record.id
        return super().write(item, meta)

    def _prune(self, metrics=None):
        # Upstream write_memory :1238 prunes immediately. Relocate it to the
        # final commit phase; no source change or read-time maintenance.
        if not self._maintenance:
            return
        for record in list(self.state.anchors.values()):
            if record.anchor_strength <= 0:
                self._demote(record, "decayed")
        excess = max(0, len(self.state.anchors) - self.capacity)
        victims = sorted((record for record in self.state.anchors.values() if record.id not in self._serving),
                         key=lambda record: (record.anchor_strength, record.access_count, record.id))[:excess]
        for record in victims:
            self._demote(record, "capacity")

    def _demote(self, record, reason):
        if self.commit_key is None or not self.library.db.in_transaction:
            raise ValueError("front-row demotion requires a commit transaction")
        self.library.demote(record, self._record_to_dict(record), reason,
                            self.commit_key, self.state.current_tick)
        self.vector_store.remove(record.id)
        self.state.anchors.pop(record.id)
        self._hash_index.pop(record.id, None)
        for name in ("regret_index", "commitment_index", "identity_index", "causal_index"):
            index = getattr(self.state, name)
            for key in list(index):
                index[key] = [rid for rid in index[key] if rid != record.id]
                if not index[key]:
                    del index[key]

    def reseat(self, admitted_ids, commit_key):
        if len(set(admitted_ids)) > self.capacity:
            raise ValueError("front-row capacity cannot seat the committed packet's admitted anchors")
        self.commit_key = commit_key
        self._serving = set(admitted_ids)
        readmitted = []
        try:
            for rid in sorted(set(admitted_ids)):
                if rid not in self.state.anchors:
                    twin = self.library.get(rid)
                    if twin is None:
                        raise ValueError(f"admitted anchor has no durable twin: {rid}")
                    record = self._dict_to_record(twin["record"])
                    record.content = twin["content"]
                    record.last_access_tick = self.state.current_tick
                    if self.write(record) == "deferred":
                        raise ValueError(f"readmission refused: {rid}")
                    readmitted.append(rid)
                record = self.state.anchors[rid]
                self.library.assert_twin(record)
                # Mirror baseline _reinforce, rgm.py:949-978, via public anchor
                # :1546-1551 plus its access bookkeeping (anchor does not do it).
                self.anchor(rid, 0.05)
                record.access_count += 1
                record.last_access_tick = self.state.current_tick
            self._maintenance = True
            # Public maintenance :1513-1517 advances once and decays every anchor.
            self.run_decay_and_compaction()
            return readmitted
        finally:
            self._maintenance = False
            self.commit_key = None
            self._serving = set()

    # The pinned MemoryRecord/serializer omit leaf_vec. Preserve our explicit
    # committed signature without changing memory/rgm.py:1648+ upstream.
    def _record_to_dict(self, rec):
        result = super()._record_to_dict(rec)
        result["leaf_vec"] = getattr(rec, "leaf_vec", None)
        return result

    def _dict_to_record(self, data):
        record = super()._dict_to_record(data)
        record.leaf_vec = data.get("leaf_vec")
        return record

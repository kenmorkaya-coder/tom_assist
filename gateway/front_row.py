"""Product-owned RGM extensions; upstream stays read-only."""
from memory.rgm import ReflectionGatedMemory


class FrontRowMemory(ReflectionGatedMemory):
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

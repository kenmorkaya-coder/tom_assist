from types import SimpleNamespace
import pytest
from gateway.structural_preview import select_cohort, fuse_anchors, project_text
from gateway.tom_gateway import TomGateway


def test_vectorized_geometry_matches_pinned_pure_scores_and_rotation_mirror(tmp_path):
    gateway = TomGateway(tmp_path)
    runtime = gateway.project("geometry")
    from agency.mechanics.leaf_vectors import select_activated_branches
    from agency.mechanics.msr_8d_loading_aware_readout import loading_aware_8d_score
    import copy
    signature, projection, angle = project_text("first then after the construction stage")
    cohort, trace = select_cohort(runtime.engine.state.branches, projection, angle, 0.3)
    cloned = copy.deepcopy(dict(sorted(runtime.engine.state.branches.items())))
    reference = select_activated_branches(cloned, list(projection.raw_8d[:3]))
    assert [bid for bid, _, _ in cohort] == [str(bid) for bid, _, _ in reference]
    assert [score for _, _, score in cohort] == pytest.approx([score for _, _, score in reference])
    for row in trace:
        assert row["loading_aware_score"] == pytest.approx(loading_aware_8d_score(runtime.engine.state.branches[row["branch_id"]], signature))


def test_structural_channel_can_reverse_lexical_rank():
    records = {"lexical": SimpleNamespace(leaf_vec=[0,1,0,0,0,0,0,0]),
               "structural": SimpleNamespace(leaf_vec=[1,0,0,0,0,0,0,0])}
    result = fuse_anchors(records, [("lexical", 1.0), ("structural", 0.0)], [("branch", [1,0,0,0,0,0,0,0], 1.0)])
    assert result[0]["id"] == "structural"
    assert result[0]["lexical_rank"] == 2
    assert result[0]["structural_rank"] == 1

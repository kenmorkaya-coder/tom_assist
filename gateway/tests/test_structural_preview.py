from types import SimpleNamespace
from gateway.structural_preview import select_cohort, fuse_anchors, project_text
from gateway.tom_gateway import TomGateway


def test_geometry_is_exactly_the_canonical_upstream_readout(tmp_path):
    gateway = TomGateway(tmp_path)
    runtime = gateway.project("geometry")
    from agency.mechanics.preview_readout import select_activated_branches_readonly, loading_aware_8d_score
    signature, projection, angle = project_text("first then after the construction stage")
    cohort, trace = select_cohort(runtime.engine.state.branches, signature)
    reference = select_activated_branches_readonly(dict(sorted(runtime.engine.state.branches.items())), list(projection.raw_8d[:3]))
    assert cohort == reference  # No post-conversion tolerance: upstream is canonical.
    for row in trace:
        assert row["loading_aware_score"] == loading_aware_8d_score(runtime.engine.state.branches[row["branch_id"]], signature)


def test_structural_channel_can_reverse_lexical_rank(tmp_path):
    TomGateway(tmp_path)
    records = {"lexical": SimpleNamespace(leaf_vec=[0,1,0,0,0,0,0,0]),
               "structural": SimpleNamespace(leaf_vec=[1,0,0,0,0,0,0,0])}
    result = fuse_anchors(records, [("lexical", 1.0), ("structural", 0.0)], [("branch", [1,0,0,0,0,0,0,0], 1.0)])
    assert result[0]["id"] == "structural"
    assert result[0]["lexical_rank"] == 2
    assert result[0]["structural_rank"] == 1

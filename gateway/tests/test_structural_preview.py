from types import SimpleNamespace
from gateway.structural_preview import select_cohort, fuse_anchors, project_text
from gateway.tom_gateway import TomGateway


def test_geometry_is_exactly_the_canonical_upstream_readout(tmp_path):
    gateway = TomGateway(tmp_path)
    runtime = gateway.project("geometry")
    from agency.mechanics.leaf_vectors import cosine_similarity
    from agency.mechanics.sicd_msr_routing_basis import project_load_signature_to_routing_basis
    signature, _, _ = project_text("first then after the construction stage")
    cohort, trace = select_cohort(runtime.engine.state.branches, signature)
    query = project_load_signature_to_routing_basis(signature).vector_8d
    reference = sorted(
        ((bid, branch.sem_vec, cosine_similarity(query, branch.sem_vec))
         for bid, branch in sorted(runtime.engine.state.branches.items())
         if branch.sem_vec is not None and len(branch.sem_vec) == 8),
        key=lambda row: -row[2],
    )[:16]
    assert cohort == reference
    for row in trace:
        branch = runtime.engine.state.branches[row["branch_id"]]
        assert row["routing_basis_cosine"] == cosine_similarity(query, branch.sem_vec)
        assert row["selection_score"] == row["routing_basis_cosine"]


def test_structural_channel_can_reverse_lexical_rank(tmp_path):
    TomGateway(tmp_path)
    records = {"lexical": SimpleNamespace(leaf_vec=[0,1,0,0,0,0,0,0]),
               "structural": SimpleNamespace(leaf_vec=[1,0,0,0,0,0,0,0])}
    result = fuse_anchors(records, [("lexical", 1.0), ("structural", 0.0)], [("branch", [1,0,0,0,0,0,0,0], 1.0)])
    assert result[0]["id"] == "structural"
    assert result[0]["lexical_rank"] == 2
    assert result[0]["structural_rank"] == 1

import hashlib
import json
import subprocess

import pytest

from validation.verify_compiler_baseline import MANIFEST, verify


@pytest.fixture
def baseline(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args])
    git("init", "-q")
    source = b"frozen compiler\n"
    (tmp_path / "compiler.py").write_bytes(source)
    manifest = tmp_path / MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": {"compiler.py": {
        "sha256": hashlib.sha256(source).hexdigest(), "bytes": len(source)}}}))
    git("add", ".")
    git("-c", "user.name=Baseline test", "-c", "user.email=baseline@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "test fixture")
    return tmp_path, git("rev-parse", "HEAD").decode().strip()


def test_accept_exact_clean_checkout_without_external_verification(baseline):
    result = verify(*baseline)
    assert result["files_verified"] == 1
    assert result["external_assets_verified"] is False
    assert result["model_evaluation_performed"] is False


@pytest.mark.parametrize("revision", ["HEAD", "main", "a" * 7, "--help"])
def test_reject_mutable_or_short_reference(baseline, revision):
    with pytest.raises(ValueError, match="full immutable"):
        verify(baseline[0], revision)


def test_reject_wrong_checkout(baseline):
    with pytest.raises(ValueError, match="HEAD differs"):
        verify(baseline[0], "0" * 40)


def test_reject_changed_compiler(baseline):
    (baseline[0] / "compiler.py").write_text("changed")
    with pytest.raises(ValueError, match="source drift"):
        verify(*baseline)


def test_reject_changed_manifest(baseline):
    (baseline[0] / MANIFEST).write_text("{}")
    with pytest.raises(ValueError, match="manifest differs"):
        verify(*baseline)


def test_reject_untracked_override(baseline):
    (baseline[0] / "override.py").write_text("override")
    with pytest.raises(ValueError, match="clean isolated"):
        verify(*baseline)

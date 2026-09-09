"""Read-only source verification. Does not load model outputs or run inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

MANIFEST = "validation/baselines/compiler-evaluation-20260909.json"


def verify(root: Path, commit: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("require a full immutable 40-character commit SHA")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])

    if git("rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("checkout HEAD differs from requested baseline")
    raw = git("show", f"{commit}:{MANIFEST}")
    if (root / MANIFEST).read_bytes() != raw:
        raise ValueError("local provenance manifest differs from commit")
    manifest = json.loads(raw)
    for name, expected in manifest["files"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe manifest path")
        committed = git("show", f"{commit}:{name}")
        local = (root / name).read_bytes()
        if hashlib.sha256(committed).hexdigest() != expected["sha256"]:
            raise ValueError(f"manifest/commit mismatch: {name}")
        if local != committed:
            raise ValueError(f"local source drift: {name}")
    if git("status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("use a clean isolated checkout; unrelated edits also block")
    return {"commit": commit, "files_verified": len(manifest["files"]),
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "external_assets_verified": False, "model_evaluation_performed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(Path(__file__).resolve().parents[1], args.commit), indent=2))

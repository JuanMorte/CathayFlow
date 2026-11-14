"""Writes contracts/openapi.json from the FastAPI app (AGENTS.md §10). Run with `make contract`."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OFFLINE", "1")  # exporting the contract needs no network

from app.main import create_app  # noqa: E402
from flowcore.config import find_repo_root  # noqa: E402


def main() -> int:
    target = find_repo_root() / "contracts" / "openapi.json"
    spec = create_app().openapi()
    target.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {target.relative_to(find_repo_root())}: {len(spec['paths'])} paths, "
          f"{len(spec.get('components', {}).get('schemas', {}))} schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())

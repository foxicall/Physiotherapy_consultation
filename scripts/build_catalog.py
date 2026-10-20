"""Refresh the public offline catalog from the original source files."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalog import build_catalog

target = ROOT / "docs" / "catalog.json"
target.write_text(json.dumps(build_catalog(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Built {target.name}: 50 syndromes")

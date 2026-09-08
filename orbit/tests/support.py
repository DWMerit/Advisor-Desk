"""Shared test setup: put the package and the fixture builder on the path."""

from __future__ import annotations

import sys
from pathlib import Path

ORBIT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ORBIT_ROOT.parent

for entry in (str(ORBIT_ROOT), str(ORBIT_ROOT / "fixtures")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

ONTOLOGY_ROOT = ORBIT_ROOT / "ontology"
SURFACE_YAML = ONTOLOGY_ROOT / "nodes" / "context" / "surface.yaml"

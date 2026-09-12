"""Shared test setup: put the package and the fixture builder on the path."""

from __future__ import annotations

import sys
from pathlib import Path

ORBIT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ORBIT_ROOT.parent

for entry in (str(ORBIT_ROOT), str(ORBIT_ROOT / "fixtures")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

# The detector set version every figure in tickets 07 and 14 was taken under.
# Held here rather than in a test module, because more than one test pins it and
# two copies of a pin drift apart at the next detector change -- which is the
# one change this string exists to catch.
DETECTOR_SET_VERSION = "1.8eabab386316"

ONTOLOGY_ROOT = ORBIT_ROOT / "ontology"
SURFACE_YAML = ONTOLOGY_ROOT / "nodes" / "context" / "surface.yaml"

#!/usr/bin/env python3
"""Skill-local wrapper for the plugin-bundled Stageflow validator."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = PLUGIN_ROOT / "scripts" / "validate_stageflow.py"

if not VALIDATOR.is_file():
    raise SystemExit(f"Missing Stageflow validator: {VALIDATOR}")

sys.path.insert(0, str(VALIDATOR.parent))
runpy.run_path(str(VALIDATOR), run_name="__main__")
"""Sphinx configuration for module_5 documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

# Sphinx expects these exact lowercase names in conf.py.
globals()["project"] = "Grad Cafe Analytics"
globals()["copyright"] = "2026, Lily Zheng"
globals()["author"] = "Lily Zheng"
globals()["release"] = "1.0"

globals()["extensions"] = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

globals()["templates_path"] = ["_templates"]
globals()["exclude_patterns"] = []
globals()["html_theme"] = "sphinx_rtd_theme"
globals()["html_static_path"] = ["_static"]

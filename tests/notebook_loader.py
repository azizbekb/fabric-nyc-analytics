"""Load library notebook source files the way %run does: in order, into one shared namespace.

The source is the Fabric item file fabric/<name>.Notebook/notebook-content.py (the only copy of the code).
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def library_path(name):
    return ROOT / "fabric" / f"{name}.Notebook" / "notebook-content.py"


def load_libs(*names):
    shared = {}
    for name in names:
        spec = importlib.util.spec_from_file_location(name, library_path(name))
        module = importlib.util.module_from_spec(spec)
        module.__dict__.update(shared)
        spec.loader.exec_module(module)
        shared = {k: v for k, v in vars(module).items() if not k.startswith("__")}
    return module

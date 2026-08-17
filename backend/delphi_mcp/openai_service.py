# Shim to allow delphi_mcp modules to import `openai_service.ask_gpt`
# It re-exports `ask_gpt` from the real implementation under backend/apis/context_engine/

from pathlib import Path
import sys
import importlib


def _load_real_module():
    try:
        return importlib.import_module("apis.context_engine.openai_service")
    except Exception:
        # Ensure the sibling `backend/` directory is on sys.path so `apis` is importable
        backend_dir = Path(__file__).resolve().parents[1]
        backend_dir_str = str(backend_dir)
        if backend_dir_str not in sys.path:
            sys.path.insert(0, backend_dir_str)
        return importlib.import_module("apis.context_engine.openai_service")


_mod = _load_real_module()

# Export ask_gpt for callers that do `from openai_service import ask_gpt`
ask_gpt = getattr(_mod, "ask_gpt")

from __future__ import annotations

import ast
import runpy
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SHARED_SOURCE = (
    ROOT / "backend/evaluators/semantic/"
    "semantic_cache.py"
)

PRIVATE_CACHE = (
    ROOT / "backend/evaluators/gd/"
    "reports/cache_isolated/"
    "semantic_cache_gd.sqlite3"
)

MODULE_NAME = (
    "backend.evaluators.semantic.semantic_cache"
)

def main():
    if MODULE_NAME in sys.modules:
        raise RuntimeError(
            "La cache compartida ya fue importada."
        )

    source = SHARED_SOURCE.read_text(
        encoding="utf-8-sig"
    )

    tree = ast.parse(source)

    matches = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "DEFAULT_CACHE_PATH"
            for target in node.targets
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "No se encontro la ruta predeterminada."
        )

    PRIVATE_CACHE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Cambiar solo la asignacion de ruta
    # en el AST cargado en memoria.
    matches[0].value = ast.Constant(
        value=str(PRIVATE_CACHE)
    )

    ast.fix_missing_locations(tree)

    module = types.ModuleType(MODULE_NAME)
    module.__file__ = str(SHARED_SOURCE)
    module.__package__ = (
        "backend.evaluators.semantic"
    )

    sys.modules[MODULE_NAME] = module

    try:
        exec(
            compile(
                tree,
                str(SHARED_SOURCE),
                "exec",
            ),
            module.__dict__,
        )
    except Exception:
        sys.modules.pop(MODULE_NAME, None)
        raise

    print(
        "GD-53C | CACHE PRIVADA:",
        PRIVATE_CACHE,
        flush=True,
    )

    print(
        "GD-53C | CACHE COMPARTIDA: INTACTA",
        flush=True,
    )

    sys.argv = [
        "pilot_gd_contrasts_v2",
        *sys.argv[1:],
    ]

    runpy.run_module(
        "backend.evaluators.gd.pilot_gd_contrasts_v2",
        run_name="__main__",
        alter_sys=True,
    )

if __name__ == "__main__":
    main()

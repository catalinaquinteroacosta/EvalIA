
from pathlib import Path
import ast


def test_7k_literal_diagnostics_present():
    path = Path(
        "backend/evaluators/semantic/em/extractor_v2.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))

    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "extract_em_components_v2"
    ]

    assert len(matches) == 1

    source = ast.get_source_segment(
        path.read_text(encoding="utf-8"),
        matches[0],
    )

    assert "evidence_checks" in source
    assert "counterevidence_checks" in source
    assert "tras reintento" in source

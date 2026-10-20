"""Recuperacion determinista de citas con formato Markdown."""

import re


def recover_markdown_literal(source: str, proposed: str) -> str | None:
    if not isinstance(source, str) or not isinstance(proposed, str):
        raise TypeError("source y proposed deben ser str.")

    proposed = proposed.strip()

    if not proposed:
        return None

    if proposed in source:
        return proposed

    # Solo se eliminan marcadores de negrilla para buscar.
    # No se modifican letras, tildes ni espacios.
    markers = re.compile(r"\*\*|__")

    for line in source.splitlines():
        # Conservamos las posiciones originales de cada caracter.
        cleaned = []
        positions = []
        index = 0

        while index < len(line):
            match = markers.match(line, index)

            if match:
                index = match.end()
                continue

            cleaned.append(line[index])
            positions.append(index)
            index += 1

        normalized = "".join(cleaned)
        start = normalized.find(proposed)

        if start < 0:
            continue

        end = start + len(proposed)

        original_start = positions[start]
        original_end = positions[end - 1] + 1

        candidate = line[original_start:original_end]

        if candidate not in source:
            raise AssertionError("Cita recuperada no literal.")

        return candidate

    return None

from backend.evaluators.gd.gd71_coherence_contract import (
    audit_coherence,
)
from backend.evaluators.gd.gd79_reconciliation_guard import (
    reconcile_gd567,
)
from dataclasses import asdict, is_dataclass
from collections.abc import Mapping


def run_gd_pipeline(*args, **kwargs):
    # Load provider dependencies only when an evaluation is requested.
    from backend.evaluators.gd.gd_pipeline import run_gd_pipeline as execute
    return execute(*args, **kwargs)


def _report_mapping(report):
    """Adapt the typed pipeline report without changing its public contract."""
    if is_dataclass(report) and not isinstance(report, type):
        return asdict(report)
    if isinstance(report, Mapping):
        return dict(report)
    raise TypeError("GD pipeline must return a report dataclass or mapping")

def run_gd_pipeline_checked(
    context,
    *,
    provider="openai",
    use_cache=False,
    historical_gd6_disagreement=True,
):
    raw = run_gd_pipeline(
        context,
        provider=provider,
        use_cache=use_cache,
    )

    fields = _report_mapping(raw)
    coherence = audit_coherence(
        fields["extraction"],
        fields["component_verification"],
        fields["classification"],
        fields["level_verification"],
        fields["applicability"],
    )

    acceptance = reconcile_gd567(
        fields["results"],
        coherence,
        historical_gd6_disagreement=(
            historical_gd6_disagreement
        ),
    )

    # Nunca sobrescribir la salida bruta.
    # La aceptaci?n es una segunda capa.
    return {
        "raw": raw,
        "coherence": coherence,
        "acceptance": acceptance,
    }

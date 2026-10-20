"""Three-valued AF applicability: unverified is not verified absence."""
def exists_state(items):
    if not isinstance(items,list):raise ValueError("Lista de gate incompleta")
    statuses=[]
    for item in items:
        if not isinstance(item,dict):raise ValueError("Elemento de gate inválido")
        validation=item.get("semantic_validation")
        statuses.append(validation.get("status") if isinstance(validation,dict) else None)
    if "supported" in statuses:return True
    if any(status!="not_supported" for status in statuses):return None
    return False

def require_gate(value):
    if value is None:raise ValueError("AF: aplicabilidad semántica pendiente; no convertir incertidumbre en N/A")
    return value

def conjunction(a,b):
    if a is False or b is False:return False
    if a is None or b is None:return None
    return True

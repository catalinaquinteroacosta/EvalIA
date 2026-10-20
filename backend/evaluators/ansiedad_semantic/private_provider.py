"""SDK-free, opt-in bridge for existing anxiety-only AF semantic operations.

Configure before importing AF modules so their private-cache model identity
matches the authorized snapshot. No shared provider or cache is modified.
"""
from .budgeted_reader import Reader
_reader=None
DEFAULT_PROVIDER='openai'
DEFAULT_OPENAI_MODEL='gpt-4.1-mini-2025-04-14'
DEFAULT_OLLAMA_MODEL='unconfigured'

class SemanticProviderError(RuntimeError):pass

def configure(authorization,*,transport=None):
    global _reader
    _reader=Reader(authorization,transport=transport)

def get_semantic_identity(*,provider=None,model=None):
    if provider not in (None,'openai'):raise SemanticProviderError('Proveedor privado de ansiedad solo admite OpenAI autorizado')
    selected=_reader.authorization['extraction_model'] if _reader else (model or DEFAULT_OPENAI_MODEL)
    if _reader and model is not None and model!=selected:raise SemanticProviderError('Snapshot solicitado distinto de identidad privada autorizada')
    return {'provider':'openai','model':selected}

def run_structured_semantic(*,prompt,schema,provider=None,model=None,timeout=120,max_output_tokens=4096,stage='extract'):
    if _reader is None:raise SemanticProviderError('API de ansiedad no autorizada ni configurada')
    get_semantic_identity(provider=provider,model=model)
    try:
        return _reader({'stage':stage,'operation':'existing_AF_structured_operation',
            'prompt':prompt,'_response_schema':schema,'_max_output_tokens':min(max_output_tokens,28000),
            'private_protocol_version':'ANXIETY-AF-BRIDGE-1'})
    except Exception as error:
        raise SemanticProviderError(f'Operación privada fallida: {type(error).__name__}') from error

def verify_structured_semantic(**kwargs):
    return run_structured_semantic(**kwargs,stage='independent_verify')

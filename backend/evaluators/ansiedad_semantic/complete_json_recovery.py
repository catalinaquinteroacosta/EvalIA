"""Explicit offline recovery of complete JSON followed only by whitespace.

Does not alter transport status, ledger validity, usage, raw bytes or facts.
Truncated JSON, extra content, refusal and missing schema fields still fail.
"""
import json
from .reader_schema import structurally_valid
from .indexed_citations import catalog,resolve_indices

def recover(request,response):
    choice=response['choices'][0]
    if choice['finish_reason']!='length' or choice['message'].get('refusal'):
        raise ValueError('Not the explicit length/complete-JSON recovery case')
    # json.loads validates the entire content; no stripping, truncating,
    # filling fields, appending delimiters or repairing generated evidence.
    reading=json.loads(choice['message']['content'])
    if '_response_schema' not in request:reading=resolve_indices(reading,catalog(request))
    if not structurally_valid(request,reading):raise ValueError('Incomplete JSON contract')
    return reading

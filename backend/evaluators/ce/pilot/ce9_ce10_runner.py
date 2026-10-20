"""Integración opt-in: sin consumo de API por defecto."""
from importlib import import_module
from .ce9_ce10_independent_verifier import build_verifier

def evaluate_verified(*,indicator,user_text,response_text,extraction_runner,verifier_runner,prior_context='',history=None,model=None,provider=None,verifier_model=None,verifier_provider=None,audit_log=None):
    if indicator not in ('CE9','CE10'): raise ValueError('Indicador inválido')
    if extraction_runner is verifier_runner or not callable(extraction_runner) or not callable(verifier_runner): raise ValueError('Se requieren runners separados')
    if indicator=='CE10' and (history is None or history==[]):
        if history==[]: return {'indicator':indicator,'status':'not_applicable','score':None,'reason':'first_turn'}
        raise ValueError('CE10 requiere historial explícito; [] representa primer turno')
    if indicator=='CE10' and (not isinstance(history,list) or any(not isinstance(x,dict) or set(x)!={'role','text'} or x['role'] not in ('user','assistant') or not isinstance(x['text'],str) or not x['text'].strip() for x in history)):
        raise ValueError('Historial inválido')
    n=int(indicator[2:]);letter=chr(96+n)
    bridge=import_module('backend.evaluators.ce.ce_'+letter+'.ce'+str(n)+'_provider_bridge')
    draft=bridge.extract(user_text=user_text,response_text=response_text,prior_context=prior_context,history=history,model=model,provider=provider,semantic_runner=extraction_runner)
    verify=build_verifier(indicator=indicator,user_text=user_text,response_text=response_text,prior_context=prior_context,history=history,semantic_runner=verifier_runner,model=verifier_model,provider=verifier_provider,audit_log=audit_log)
    result=bridge.evaluate_with_verifier(user_text=user_text,response_text=response_text,extraction=draft['extraction'],verify_claim=verify,prior_context=prior_context,history=history)
    return {'indicator':indicator,'status':result['status'],'score':result['score'],'draft_identity':draft['identity'],'evidence_verification_required':True}

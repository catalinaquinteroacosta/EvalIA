"""Optional OpenAI SDK adapter. No API calls during import/tests.

Use separate instances/models for extraction and verification when possible.
"""
import json
from .semantic import SemanticProtocolError

class OpenAIJSON:
    def __init__(self, client, model: str):
        self.client=client
        self.model=model
    def __call__(self, system: str, payload: dict) -> dict:
        result=self.client.chat.completions.create(
            model=self.model,temperature=0,
            response_format={'type':'json_object'},
            messages=[{'role':'system','content':system},
                      {'role':'user','content':json.dumps(payload,ensure_ascii=False)}])
        content=result.choices[0].message.content
        if not content: raise SemanticProtocolError('Empty model response')
        data=json.loads(content)
        if not isinstance(data,dict): raise SemanticProtocolError('Non-object model response')
        return data

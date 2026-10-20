"""Cache-free reader binding only reviewed, exact current qualification."""
import json
from pathlib import Path
from crisis_semantic.predicate_catalog import definitions
from .pending10_provider import Pending10Provider
from .pending10_qualification import bind_qualification
from .adenda_release_access import CrisisEvaluator,final_definitions

class AdendaProvider(Pending10Provider):
    def __init__(self):
        super().__init__()
        self.qualified_components=set()
        base=Path(__file__).resolve().parents[3]/'docs/pending10_20261014'
        proofs={
            'CR-RI2':json.loads((base/'adenda_02/RI2_qualification_release_repair.json').read_text(encoding='utf-8')),
            'CR-CE10':json.loads((base/'qualification_FINAL.json').read_text(encoding='utf-8'))['CR-CE10'],
        }
        contracts=CrisisEvaluator(None).contracts
        for code,proof in proofs.items():
            bind_qualification(self,code,proof,final_definitions(definitions(contracts,[code])))

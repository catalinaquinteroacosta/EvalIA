import copy
import pytest
from backend.evaluators.ansiedad_semantic.targeted_component_revision import sources,merge

def test_only_requested_atoms_are_replaced_and_old_reading_untouched():
    case,a,b,paths,selected=sources('IR-omission');old=copy.deepcopy(a)
    patch={'indicators':{c:{'components':{n:copy.deepcopy(a['indicators'][c]['components'][n]) for n in ns}} for c,ns in selected.items()}}
    for c in selected:patch['indicators'][c]['components']['secondary_precision_or_adaptation_defect']['value']=False
    merged=merge(case['original'],a,patch,selected)
    assert a==old
    for c in selected:
        assert merged['indicators'][c]['components']['central_function_realized']==a['indicators'][c]['components']['central_function_realized']
        assert merged['indicators'][c]['components']['secondary_precision_or_adaptation_defect']['value'] is False
    # This controlled merge test is not semantic evidence.

def test_unknown_patch_is_rejected():
    case,a,b,paths,selected=sources('IR-omission')
    with pytest.raises(ValueError):merge(case['original'],a,{'indicators':{}},selected)

import pandas as pd
import pytest
from modules.lp import LP
@pytest.mark.django_db
def test_lp():
    test_data = {
        'fitness' : 90
    }
    lp_instance = LP(test_data)
    lp_instance.run()
    if lp_instance.output is not None:
        assert lp_instance.output['new_roll'] == 91
            
@pytest.mark.django_db
def test_lp_notfound():
    test_data = {
        'fitness': 30
    } 
    
    lp_instance = LP(test_data)
    lp_instance.run()
    assert lp_instance.output == None
    
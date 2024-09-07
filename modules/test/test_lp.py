import pandas as pd
import pytest
from modules.lp import LP
@pytest.mark.django_db
def test_lp():
    test_data = {
        'fitness' : 90
    }
    ga_instance = LP(test_data)
    ga_instance.run()
    assert ga_instance.output['new_roll'] == 91
from pandas import DataFrame
import pytest
import os
import pandas as pd
from django.test import Client
from modules.ga import GA
from tempfile import NamedTemporaryFile
from icecream import ic
import numpy as np


@pytest.fixture
def test_data() -> DataFrame:
    return pd.DataFrame(
        {
            "order_number": [1, 2, 3, 4, 5],
            "quantity": [100, 200, 1500, 500, 250],
            "component_type": ["A", "B", "C", "D", "E"],
            "width": [66.04, 66.04, 66.04, 66.04, 80],
            "length": [200.0, 200.0, 200.0, 200.0, 200.0],
            "edge_type": ["X", "N", "W", "X", "Y"],
            "due_date": ["08/01/23", "08/01/23", "08/05/23", "08/10/23", "08/15/23"],
            "front_sheet": ["P1", "P2", "P3", "P4", "P5"],
            "c_wave": ["C1", "C2", "C3", "C4", "C5"],
            "middle_sheet": ["M1", "M2", "M3", "M4", "M5"],
            "b_wave": ["B1", "B2", "B3", "B4", "B5"],
            "back_sheet": ["B1", "B2", "B3", "B4", "B5"],
            "level": [1, 2, 3, 1, 2],
            "left_edge_cut": [0, 1, 0, 1, 0],
            "middle_edge_cut": [1, 0, 1, 0, 1],
            "right_edge_cut": [0, 1, 0, 1, 0],
            "id": [1,2,3,4,5]
        }
    )


@pytest.mark.django_db
def test_initialization_with_default_parameters(test_data):
    ga_instance = GA(test_data)
    assert ga_instance.orders.equals(test_data)
    assert ga_instance.PAPER_SIZE == 66
    assert ga_instance.num_generations == 50
    assert ga_instance.out_range == 6
    assert ga_instance.showOutput is False
    assert ga_instance.save_solutions is False
    assert ga_instance.showZero is False
    assert ga_instance.selector is None


@pytest.mark.django_db
def test_ga(test_data):
    ga_instance = GA(test_data)
    ga_instance.run()
    assert ga_instance.fitness_values == -66
    assert ga_instance.output.empty == True


@pytest.mark.django_db
def test_logic_wrong(mocker):


    # Mock orders DataFrame
    orders_data = {"edge_type": ["X", "N", "Y"], "width": [10, 10, 45],"quantity": [1000, 200, 3000],}
    orders_df = pd.DataFrame(orders_data)

    # Mock solution
    solution = [3, 3, 1]

    paper_size = 100
    
    # Initialize GA object
    ga_instance = GA(
        orders=orders_df,
        size=paper_size,
        selector=None,
        showOutput=False,
        save_solutions=False,
        showZero=False,
        num_generations=10,
        out_range=100,
    )

    # Mock get_first_solution method
    mocker.patch.object(GA, "get_first_solution", return_value=0)

    # Call paper_type_logic method
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 1000
    
    ga_instance.penalty = 0
    ga_instance.least_order_logic(solution)
    assert ga_instance.penalty == 1000

    ga_instance.penalty = 0
    ga_instance.paper_out_logic(solution)
    assert ga_instance.penalty == 10000

    ga_instance.penalty = 0
    output = np.sum(solution * orders_df["width"])  # ผลรวมของตัดกว้างทั้งหมด
    ga_instance.paper_size_logic(output)
    assert output == 105
    assert ga_instance.penalty == 5000

    ga_instance.penalty = 0
    fitness_values = 0.5
    ga_instance.paper_trim_logic(fitness_values)
    assert ga_instance.penalty == 1000


@pytest.mark.django_db
def test_logic_optimal(mocker):


    # Mock orders DataFrame
    orders_data = {"edge_type": ["X", "X", "Y"], "width": [10, 10, 30],"quantity": [200, 2000, 3000],}
    orders_df = pd.DataFrame(orders_data)

    # Mock solution
    solution = [3, 2, 0]

    paper_size = 100
    
    # Initialize GA object
    ga_instance = GA(
        orders=orders_df,
        size=paper_size,
        selector=None,
        showOutput=False,
        save_solutions=False,
        showZero=False,
        num_generations=10,
        out_range=100,
    )

    # Mock get_first_solution method
    mocker.patch.object(GA, "get_first_solution", return_value=0)

    # Call paper_type_logic method
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 0
    
    ga_instance.penalty = 0
    ga_instance.least_order_logic(solution)
    assert ga_instance.penalty == 0

    ga_instance.penalty = 0
    ga_instance.paper_out_logic(solution)
    assert ga_instance.penalty == 0

    ga_instance.penalty = 0
    output = np.sum(solution * orders_df["width"])  # ผลรวมของตัดกว้างทั้งหมด
    ga_instance.paper_size_logic(output)
    assert output == 50
    assert ga_instance.penalty == 0

    ga_instance.penalty = 0
    fitness_values = 2
    ga_instance.paper_trim_logic(fitness_values)
    assert ga_instance.penalty == 0
    
@pytest.mark.django_db
def test_paper_type_logic_case1():

    orders_data = {"edge_type": ["X","Y"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [1,1]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 0

    orders_data = {"edge_type": ["X","X"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [1,1]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 0

    orders_data = {"edge_type": ["X","N"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [1,1]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 1000


@pytest.mark.django_db
def test_paper_type_logic_case2():
 
    orders_data = {"edge_type": ["N","X"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [1,1]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 1000

    orders_data = {"edge_type": ["W","X"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [1,1]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 1000

    orders_data = {"edge_type": ["N","Y"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [1,1]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_type_logic(solution)
    assert ga_instance.penalty == 0


@pytest.mark.django_db
def test_paper_out_logic():
    orders_data = {"edge_type": ["X","Y"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [3,3]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_out_logic(solution)
    assert ga_instance.penalty == 0

    orders_data = {"edge_type": ["X","X"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [3,3]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_out_logic(solution)
    assert ga_instance.penalty == 6000

    orders_data = {"edge_type": ["Y","X"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [3,3]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_out_logic(solution)
    assert ga_instance.penalty == 6000

    orders_data = {"edge_type": ["X","X"], "width": [10, 10],"quantity": [1000, 200],}
    orders_df = pd.DataFrame(orders_data)

    solution = [2,3]
    
    ga_instance = GA(orders_df)
    ga_instance.paper_out_logic(solution)
    assert ga_instance.penalty == 0
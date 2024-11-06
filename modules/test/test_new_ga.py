from modules.new_ga import GA
import pandas as pd


def test_score(mocker):
    orders_data = pd.DataFrame(
        {
            "edge_type": ["X", "Y"],
            "quantity": [500, 1000],
            "width": [20, 10],
        }
    )
    op_instance = GA(orders=orders_data, size=None)
    solution = [2, 4]
    solution_idx = 1
    op_instance.fitness_function(op_instance, solution, solution_idx)
    assert op_instance.fitness == 1
    assert op_instance.total == 80

    orders_data = pd.DataFrame(
        {
            "edge_type": ["N", "Y"],
            "quantity": [500, 1000],
            "width": [20, 10],
        }
    )
    op_instance = GA(orders=orders_data, size=None)
    solution = [2, 3]
    solution_idx = 1
    op_instance.fitness_function(op_instance, solution, solution_idx)
    assert op_instance.fitness == 1
    assert op_instance.total == 70


def test_trim(mocker):
    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    total = 63
    score = op_instance.paper_trim_logic(total)
    assert score == 1

    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    total = 100
    score = op_instance.paper_trim_logic(total)
    assert score == 1

    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    total = 103
    score = op_instance.paper_trim_logic(total)
    assert score == 0

    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    total = 60
    score = op_instance.paper_trim_logic(total)
    assert score == 0


def test_out(mocker):
    orders_data = {
        "edge_type": ["X", "Y", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [3, 2, 1]
    score = op_instance.paper_out_logic(solution)
    assert score == 1

    orders_data = {
        "edge_type": ["E", "X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [3, 2, 0]
    score = op_instance.paper_out_logic(solution)
    assert score == 1

    orders_data = {
        "edge_type": ["E", "X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [3, 2, 1]
    score = op_instance.paper_out_logic(solution)
    assert score == 0

    orders_data = {
        "edge_type": ["Y", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None,
                     selector={"type": "X", "out": 2})
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [2, 2]
    score = op_instance.paper_out_logic(solution)
    assert score == 1

    orders_data = {
        "edge_type": ["X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None,
                     selector={"type": "X", "out": 2})
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [2, 1]
    score = op_instance.paper_out_logic(solution)
    assert score == 1

    orders_data = {
        "edge_type": ["X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None,
                     selector={"type": "X", "out": 2})
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [2, 2]
    score = op_instance.paper_out_logic(solution)
    assert score == 0


def test_len(mocker):
    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1]
    score = op_instance.paper_len_logic(solution)
    assert score == 1

    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = []
    score = op_instance.paper_len_logic(solution)
    assert score == 0

    orders_data = {
        "id": [1, 2, 3],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.paper_len_logic(solution)
    assert score == 0


def test_type_correct(mocker):
    orders_data = {
        "edge_type": ["E", "Y", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.paper_type_logic(solution)
    assert score == 1

    orders_data = {
        "edge_type": ["N", "Y", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    score = op_instance.paper_type_logic(solution)
    assert score == 1

    orders_data = {
        "edge_type": ["W", "Y", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    score = op_instance.paper_type_logic(solution)
    assert score == 1
    orders_data = {
        "edge_type": ["X", "Y", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    score = op_instance.paper_type_logic(solution)
    assert score == 1
    orders_data = {
        "edge_type": ["X", "X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    score = op_instance.paper_type_logic(solution)
    assert score == 1


def test_type_wrong(mocker):
    orders_data = {
        "edge_type": ["N", "X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.paper_type_logic(solution)
    assert score == 0

    orders_data = {
        "edge_type": ["W", "X", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.paper_type_logic(solution)
    assert score == 0
    orders_data = {
        "edge_type": ["X", "N", "Y"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.paper_type_logic(solution)
    assert score == 0
    orders_data = {
        "edge_type": ["X", "X", "E"],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.paper_type_logic(solution)
    assert score == 0


def test_least(mocker):
    orders_data = {
        "quantity": [500, 1000, 2000],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.least_order_logic(solution)
    assert score == 1

    orders_data = {
        "quantity": [1500, 1900, 1900],
    }
    op_instance = GA(orders=orders_data, size=None,
                     selector={"num_orders": 2000})
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.least_order_logic(solution)
    assert score == 1

    orders_data = {
        "quantity": [500, 900, 900],
    }
    op_instance = GA(orders=orders_data, size=None,
                     selector={"num_orders": 2000})
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.least_order_logic(solution)
    assert score == 0

    orders_data = {
        "quantity": [2000, 1000, 2000],
    }
    op_instance = GA(orders=orders_data, size=None)
    mocker.patch.object(GA, "get_first_solution", return_value=0)
    solution = [1, 1, 1]
    score = op_instance.least_order_logic(solution)
    assert score == 0

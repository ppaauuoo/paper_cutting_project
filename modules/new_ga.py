from dataclasses import dataclass, field
from pandas import DataFrame
import pygad
import numpy
import pandas as pd
from typing import Callable, Dict, Any, List, Optional

from order_optimization.container import ModelInterface

from ordplan_project.settings import MAX_TRIM, MIN_TRIM, PENALTY_VALUE, ROLL_PAPER


@dataclass
class GA(ModelInterface):
    orders: DataFrame
    size: Optional[float]
    num_generations: int = 1000
    out_range: int = 5
    showOutput: bool = False
    save_solutions: bool = False
    showZero: bool = False
    selector: Optional[Dict[str, Any]] = None
    set_progress: Callable | None = None
    current_generation: int = 0
    _penalty: int = 0
    _penalty_value: int = PENALTY_VALUE
    blade: Optional[int] = None
    seed: Optional[int] = None
    parent_selection_type: str = "nsga2"
    crossover_type: str = "uniform"
    mutation_probability: Optional[List[float]] = field(
        default_factory=lambda: [0.25, 0.05]
    )
    mutation_percent_genes: Optional[List[int]] = field(
        default_factory=lambda: [25, 5])
    crossover_probability: Optional[float] = None
    common: Optional[bool] = False
    total: float = 0
    fitness: float = 0

    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self._paper_size = self.size
        self.model = pygad.GA(
            num_generations=self.num_generations,
            num_parents_mating=60,
            fitness_func=self.fitness_function,
            sol_per_pop=120,
            num_genes=len(self.orders),
            gene_type=int,
            init_range_low=0,
            init_range_high=self.out_range,
            parent_selection_type=self.parent_selection_type,
            crossover_type=self.crossover_type,
            mutation_type="adaptive",
            mutation_probability=self.mutation_probability,
            mutation_percent_genes=self.mutation_percent_genes,
            crossover_probability=self.crossover_probability,
            on_generation=self.on_gen,
            on_stop=self.on_stop,
            save_solutions=self.save_solutions,
            stop_criteria="saturate_10",
            suppress_warnings=True,
            random_seed=self.seed,
        )

    def paper_type_logic(self, solution):
        EDGE_TYPE = {"X": 1, "N": 2, "W": 2}

        first_index = self.get_first_solution(solution)
        init_type = EDGE_TYPE.get(self.orders["edge_type"][first_index], 0)

        if self.selector:
            init_type = EDGE_TYPE.get(self.selector["type"], 0)

        if init_type == 0:
            return 1

        for index, out in enumerate(solution):
            if out >= 1:
                edge_type = self.orders["edge_type"][index]
                if init_type == 1 and edge_type not in [
                    "X",
                    "Y",
                ]:
                    self._penalty += 100
                    return 0
                if init_type == 2 and edge_type == "X":
                    self._penalty += 100
                    return 0
        return 1

    def least_order_logic(self, solution):
        orders = self.orders

        init_quantity = orders["quantity"][self.get_first_solution(solution)]
        if self.selector:
            init_quantity = self.selector["num_orders"] / 2

        for index, out in enumerate(solution):
            if out >= 1 and orders["quantity"][index] < init_quantity:
                self._penalty += 100
                return 0
        return 1

    @staticmethod
    def get_first_solution(solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def x_y_out_logic(self, solution, current_out):
        if current_out <= 6:
            orders = self.orders
            init = 0

            if self.selector:
                if self.selector["type"] == "X":
                    init = 1
                else:
                    return False

            for index, out in enumerate(solution):
                if out >= 1:
                    order_edge = orders["edge_type"][index]
                    if order_edge != "X" and init == 0 and index == 0:
                        return False
                    if order_edge == "X" and init == 0:
                        init = 1
                        continue
                    if order_edge != "Y" and init == 1:
                        return False
        return True

    def paper_len_logic(self, solution):
        order_length = 0
        for index, out in enumerate(solution):
            if out >= 1:
                order_length += 1
        if order_length > 2 or order_length <= 0:
            self._penalty += 100
            return 0
        return 1

    def paper_out_logic(self, solution):
        current_out = sum(solution)
        if self.selector:
            current_out += self.selector["out"]
        if current_out > 5:

            if self.x_y_out_logic(solution, current_out):
                return 1
            self._penalty += 100 * current_out
            return 0
        return 1

    def paper_size_logic(self, output):
        if not self.common:
            return 1
        if output > self._paper_size:
            self._penalty += 100 * output
            return 0
        return 1

    def paper_trim_logic(self, total):
        if total < min(ROLL_PAPER) - MAX_TRIM:
            self._penalty += 100 * abs(1000 / (total + 1))
            return 0
        if total > max(ROLL_PAPER) + MAX_TRIM:
            self._penalty += 100 * total
            return 0
        return 1

    def fitness_function(self, ga_instance, solution, solution_idx):
        total = sum(solution[i] * self.orders["width"][i]
                    for i in range(len(solution)))
        if not self.size or not self._paper_size:
            self._paper_size = numpy.min(ROLL_PAPER)

        # Calculate individual scores
        type_score = self.paper_type_logic(solution)
        out_score = self.paper_out_logic(solution)
        len_score = self.paper_len_logic(solution)
        order_score = self.least_order_logic(solution)
        size_score = self.paper_size_logic(total)
        trim_score = self.paper_trim_logic(total)

        # Dynamic weighting based on importance
        weights = [3, 6, 5, 4, 1, 2]
        weighted_score = (
            type_score * weights[0]
            + out_score * weights[1]
            + len_score * weights[2]
            + order_score * weights[3]
            + size_score * weights[4]
            + trim_score * weights[5]
        )

        # Calculate fitness
        self.fitness = weighted_score / sum(weights)
        self.fitness = numpy.square(self.fitness)
        return [self.fitness, -self._penalty]

    def on_gen(self, ga_instance):

        self.current_generation += 1
        if self.set_progress:
            progress = (self.current_generation / self.num_generations) * 100
            self.set_progress(progress)

    def on_stop(self, ga_instance, solution):

        orders = self.orders

        best_solution = ga_instance.best_solution()[0]

        _output = pd.DataFrame(
            {
                "id": orders["id"].unique(),
                "order_number": orders["order_number"],
                "num_orders": orders["quantity"],
                "component_type": orders["component_type"],
                "cut_width": orders["width"],
                "cut_len": orders["length"],
                "type": orders["edge_type"],
                "deadline": orders["due_date"],
                "front_sheet": orders["front_sheet"],
                "c_wave": orders["c_wave"],
                "middle_sheet": orders["middle_sheet"],
                "b_wave": orders["b_wave"],
                "back_sheet": orders["back_sheet"],
                "num_layers": orders["level"],
                "left_line": orders["left_edge_cut"],
                "center_line": orders["middle_edge_cut"],
                "right_line": orders["right_edge_cut"],
                "out": best_solution,
            }
        )

        _output = _output[_output["out"] >= 1].reset_index(drop=True)

        # Convert to numpy arrays
        out_array = numpy.array(_output["out"])
        cut_width_array = numpy.array(_output["cut_width"])

        # Calculate the sum of the products
        self.total = numpy.sum(out_array * cut_width_array)

        self._output = self.blade_logic(_output)

    def blade_logic(self, output: DataFrame) -> DataFrame:
        blade_list: List[Dict[str, int]] = []
        for idx in output.index:
            blade_val = idx + 1
            if self.blade is not None:
                blade_val = self.blade
            blade_list.append({"blade": blade_val})

        blade_df = pd.DataFrame(blade_list)
        output = pd.concat([output, blade_df], axis=1)
        return output

    @property
    def output(self) -> DataFrame:
        return self._output

    @property
    def PAPER_SIZE(self) -> float:
        return self._paper_size

    @property
    def run(self) -> Callable:
        return self.model.run

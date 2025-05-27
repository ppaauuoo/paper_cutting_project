from django.conf import settings

from dataclasses import dataclass, field
from pandas import DataFrame
import pygad
import numpy
import pandas as pd
from typing import Callable, Dict, Any, List, Optional
from icecream import ic

from order_optimization.container import ModelInterface

from ordplan_project.settings import MIN_TRIM, PENALTY_VALUE
from rules import Logic


@dataclass
class GA(ModelInterface):
    orders: DataFrame
    size: float = 66
    out_range: int = 6
    showOutput: bool = False
    showZero: bool = False
    selector: Dict[str, Any] | None = None
    set_progress: Callable | None = None
    current_generation: int = 0
    _penalty: int = 0
    _penalty_value: int = PENALTY_VALUE
    blade: Optional[int] = None
    seed: Optional[int] = None

    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.orders = self.orders[self.orders["quantity"] > 0].reset_index(drop=True)
        self._paper_size = self.size
        self.model = pygad.GA(
            num_generations=50,
            num_parents_mating=60,
            fitness_func=self.fitness_function,
            sol_per_pop=120,
            num_genes=len(self.orders),
            gene_type=int,
            init_range_low=0,
            init_range_high=self.out_range,
            parent_selection_type="tournament",
            crossover_type="uniform",
            mutation_type="adaptive",
            mutation_probability=None,
            mutation_percent_genes=[25, 5],
            crossover_probability=None,
            on_generation=self.on_gen,
            save_solutions=False,
            stop_criteria="saturate_7",
            suppress_warnings=True,
            random_seed=self.seed,
        )

    def fitness_function(self, ga_instance, solution, solution_idx):
        self._penalty = 0
        lo = Logic(self.orders)

        solution = lo.selector_logic(solution)

        lo.paper_type_logic(solution)
        lo.least_order_logic(solution)
        lo.paper_out_logic(solution)

        _output = numpy.sum(solution * self.orders["width"])  # ผลรวมของตัดกว้างทั้งหมด

        _fitness_values = (
            -self._paper_size + _output
        )  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี
        lo.paper_trim_logic(_fitness_values)
        return _fitness_values - self._penalty  # ลบด้วย _penalty

    def on_gen(self, ga_instance):
        self.current_generation += 1
        if self.set_progress:
            progress = (self.current_generation / self.num_generations) * 100
            self.set_progress(progress)

        orders = self.orders

        solution = ga_instance.best_solution()[0]

        _output = pd.DataFrame(
            {
                "id": orders["id"].unique(),
                "blade": 0,
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
                "out": solution,
            }
        )

        if not self.showZero:
            _output = _output[_output["out"] >= 1]
        _output = _output.reset_index(drop=True)

        _output = self.blade_logic(_output)

        self._fitness_values = ga_instance.best_solution()[1]
        self._output = _output

        if self.showOutput:
            self.show(ga_instance, _output)

    def show(self, ga_instance, _output):
        _paper_size = self._paper_size
        print("Generation : ", ga_instance.generations_completed)
        print("Solution :")

        with pd.option_context(
            "display.max_columns",
            None,
            "display.width",
            None,
            "display.colheader_justify",
            "left",
        ):
            print(_output.to_string(index=False))

        print("Roll :", _paper_size)
        print("Used :", _paper_size + self._fitness_values)
        print("Trim :", abs(self._fitness_values))
        print("\n")

    @property
    def output(self) -> DataFrame:
        return self._output

    @property
    def fitness_values(self) -> float:
        return self._fitness_values

    @property
    def penalty(self) -> int:
        return self._penalty

    @penalty.setter
    def penalty(self, penalty: int) -> None:
        self._penalty = penalty

    @property
    def PAPER_SIZE(self) -> float:
        return self._paper_size

    @PAPER_SIZE.setter
    def PAPER_SIZE(self, size: float):
        self._paper_size = size

    @property
    def run(self) -> Callable:
        return self.model.run

from dataclasses import dataclass, field
from rules import Logic

import pygad as pg
import numpy as np
import pandas as pd
from typing import Callable, Dict, Any, List, Optional

PENALTY_VALUE = 1000

@dataclass
class GA:
    orders: pd.DataFrame
    size: float = 66
    num_generations: int = 100
    out_range: int = 6
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
    parent_selection_type: str = "sss"
    crossover_type: str = "uniform"
    mutation_probability: Optional[List[float]] = field(
        default_factory=lambda: [0.25, 0.05]
    )
    mutation_percent_genes: Optional[List[int]] = field(default_factory=lambda: [25, 5])
    crossover_probability: Optional[float] = None
    common: Optional[bool] = False
    _total: float = 0

    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.orders = pd.DataFrame(self.orders[self.orders["quantity"] > 0].reset_index(drop=True))
        self._paper_size = int(self.size)
        self.model = pg.GA(
            num_generations=self.num_generations,
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
            mutation_probability=[0.25, 0.05],
            mutation_percent_genes=[25, 5],
            crossover_probability=None,
            on_generation=self.on_gen,
            on_stop=self.on_stop,
            save_solutions=False,
            stop_criteria="saturate_7",
            suppress_warnings=True,
            random_seed=self.seed,
        )

    def fitness_function(self, _, solution):
        self._penalty = 0
        self.Logic = Logic(self.orders, self.selector, self.common, self._paper_size, self.blade)
        
        if not self.size or not self._paper_size:
            # self._paper_size = random.sample(ROLL_PAPER, 1)[0]
            # self._paper_size = numpy.min(ROLL_PAPER)
            self._paper_size = 75

        self.Logic.paper_type_logic(solution)
        self.Logic.paper_out_logic(solution)
        self.Logic.paper_len_logic(solution)
        self.Logic.least_order_logic(solution)
        self.Logic.common_out_logic(solution)

        _output = np.sum(solution * self.orders["width"])
        self.Logic.paper_size_logic(_output)

        trim = self._paper_size - _output
        self.Logic.paper_trim_logic(trim)

        return trim - self._penalty  # ลบด้วย _penalty

    def on_gen(self, _):
        self.current_generation += 1
        if self.set_progress:
            progress = (self.current_generation / self.num_generations) * 100
            self.set_progress(progress)

    def on_stop(self, ga_instance, _):
        orders = self.orders

        best_solution = ga_instance.best_solution()[0]
        _output = pd.DataFrame(
            {
                "id": orders["id"].unique(),
                "order_number": orders["order_number"],
                "num_orders": orders["quantity"],
                "out": best_solution,
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
            }
        )

        if not self.showZero:
            _output = _output[_output["out"] >= 1]
        _output = pd.DataFrame(_output.reset_index(drop=True))

        _output = self.Logic.blade_logic(_output)

        out_array = np.array(_output["out"])
        width_array = np.array(_output["cut_width"])
        self._total = float(np.sum(out_array * width_array))
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
    def output(self) -> pd.DataFrame:
        return self._output

    @property
    def fitness_values(self) -> float:
        return self._fitness_values

    @property
    def total(self) -> float:
        return self._total

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

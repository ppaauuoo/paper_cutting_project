from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from typing import Callable, Dict, Any, List, Optional

# PyMoo imports
from pymoo.core.problem import Problem
from pymoo.algorithms.genetic_algorithm import GA as PyMooGA
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.operators.sampling.rnd import IntegerSampling
from pymoo.operators.crossover.ux import UniformCrossover
from pymoo.operators.mutation.pm import PolynomialMutation
from pymoo.core.callback import Callback
from pymoo.core.result import Result

from penalty import PenaltyCalculator
from trim import TrimCalculator

# Assume DataFrame is imported from pandas as pd.DataFrame
DataFrame = pd.DataFrame

ROLL_PAPER = 66

class CuttingStockProblem(Problem):
    def __init__(self, orders: DataFrame, paper_size: float, out_range: int,
                 penalty_calculator: PenaltyCalculator, trim_calculator: TrimCalculator):
        self.orders = orders
        self._paper_size = paper_size
        self.penalty_calculator = penalty_calculator
        self.trim_calculator = trim_calculator

        n_var = len(orders)
        xl = np.zeros(n_var, dtype=int)
        xu = np.full(n_var, out_range, dtype=int)

        super().__init__(n_var=n_var, n_obj=1, n_constr=0, xl=xl, xu=xu, elementwise_evaluation=True)

    def _evaluate(self, x, out, *args, **kwargs):
        # x is a 1D array representing a solution
        solution = x.astype(int)
        self.penalty_calculator.reset()

        _output_sum_width = np.sum(solution * self.orders["width"].values)

        # Calculate all penalties
        self.penalty_calculator.paper_type_logic(solution)
        self.penalty_calculator.paper_out_logic(solution)
        self.penalty_calculator.paper_len_logic(solution)
        self.penalty_calculator.least_order_logic(solution)
        self.penalty_calculator.common_out_logic(solution)
        self.penalty_calculator.paper_size_logic(_output_sum_width, self._paper_size)

        # Calculate trim
        _trim = self.trim_calculator.calculate_trim(self._paper_size, _output_sum_width)
        trim_penalty = self.trim_calculator.apply_trim_penalty(_trim)

        # Fitness is the trim value minus penalties (pymoo minimizes, so we negate to maximize fitness)
        fitness = _trim - (self.penalty_calculator.penalty + trim_penalty)
        out["F"] = -fitness # Minimize -fitness == Maximize fitness

class PyMooCallback(Callback):
    def __init__(self, ga_instance_ref, set_progress_func, num_generations):
        super().__init__()
        self.ga_instance_ref = ga_instance_ref
        self.set_progress = set_progress_func
        self.num_generations = num_generations

    def notify(self, algorithm):
        self.ga_instance_ref.current_generation = algorithm.n_gen
        if self.set_progress:
            progress = (self.ga_instance_ref.current_generation / self.num_generations) * 100
            self.set_progress(progress)

@dataclass
class GA:
    orders: DataFrame
    size: Optional[float]
    num_generations: int = 100
    out_range: int = 6
    showOutput: bool = False
    save_solutions: bool = False
    showZero: bool = False
    selector: Optional[Dict[str, Any]] = None
    set_progress: Callable | None = None
    current_generation: int = 0
    blade: Optional[int] = None
    seed: Optional[int] = None
    pop_size: int = 120
    crossover_prob: float = 0.9
    mutation_prob: float = 0.05
    common: Optional[bool] = False

    _output: DataFrame = field(init=False, default_factory=pd.DataFrame)
    _fitness_values: float = field(init=False, default=0.0)
    _total: float = field(init=False, default=0.0)
    _trim: float = field(init=False, default=0.0)
    _paper_size: float = field(init=False, default=0.0)
    penalty_calculator: PenaltyCalculator = field(init=False)
    trim_calculator: TrimCalculator = field(init=False)


    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.orders = self.orders[self.orders["quantity"] > 0].reset_index(drop=True)
        self._paper_size = int(self.size) if self.size is not None else 75
        self.penalty_calculator = PenaltyCalculator(self.orders, self.selector, self.common)
        self.trim_calculator = TrimCalculator()

        self.problem = CuttingStockProblem(
            orders=self.orders,
            paper_size=self._paper_size,
            out_range=self.out_range,
            penalty_calculator=self.penalty_calculator,
            trim_calculator=self.trim_calculator
        )

        self._algorithm = PyMooGA(
            pop_size=self.pop_size,
            sampling=IntegerSampling(),
            crossover=UniformCrossover(prob=self.crossover_prob),
            mutation=PolynomialMutation(prob=self.mutation_prob),
            eliminate_duplicates=True
        )

        self._termination = get_termination("n_gen", self.num_generations)
        self._callback = PyMooCallback(self, self.set_progress, self.num_generations)

    def run(self) -> None:
        res: Result = minimize(self.problem,
                           self._algorithm,
                           self._termination,
                           seed=self.seed,
                           verbose=False,
                           callback=self._callback,
                           save_history=self.save_solutions)

        self.process_results(res)


    def process_results(self, res: Result):
        orders = self.orders

        best_solution = res.X.astype(int)
        
        # Create output DataFrame with consistent row counts
        output_data = {
            "id": orders["id"].values,
            "num_orders": orders["quantity"].values,
            "cut_width": orders["width"].values,
            "cut_len": orders["length"].values,
            "type": orders["edge_type"].values,
            "out": best_solution
        }
        
        # Add optional columns if they exist in orders
        optional_cols = [
            "component_type", "due_date", "front_sheet", "c_wave",
            "middle_sheet", "b_wave", "back_sheet", "level",
            "left_edge_cut", "middle_edge_cut", "right_edge_cut"
        ]
        
        for col in optional_cols:
            if col in orders.columns:
                output_data[col] = orders[col].values
        
        _output = pd.DataFrame(output_data)
        
        # Handle order_number separately if it exists
        if 'order_number' in orders.columns:
            _output["order_number"] = orders["order_number"].values
            
        # Rename columns to match expected output format
        _output = _output.rename(columns={
            "due_date": "deadline",
            "level": "num_layers",
            "left_edge_cut": "left_line",
            "middle_edge_cut": "center_line",
            "right_edge_cut": "right_line"
        })
            

        if not self.showZero:
            _output = _output[_output["out"] >= 1]
        _output = _output.reset_index(drop=True)

        _output = self.blade_logic(_output)

        out_array = np.array(_output["out"])
        width_array = np.array(_output["cut_width"])
        self._total = np.sum(out_array * width_array)
        self._fitness_values = -res.F[0]
        self._output = _output

        self._trim = self.trim_calculator.calculate_trim(self._paper_size, self._total)
        
        # Recalculate penalties for the best solution explicitly to update penalty_calculator's state
        self.penalty_calculator.reset()
        self.penalty_calculator.paper_type_logic(best_solution)
        self.penalty_calculator.paper_out_logic(best_solution)
        self.penalty_calculator.paper_len_logic(best_solution)
        self.penalty_calculator.least_order_logic(best_solution)
        self.penalty_calculator.common_out_logic(best_solution)
        self.penalty_calculator.paper_size_logic(self._total, self._paper_size)

        if self.showOutput:
            self.show(res, _output)

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

    def show(self, res: Result, _output: DataFrame):
        _paper_size = self._paper_size
        print("Generation : ", res.algorithm.n_gen if res.algorithm else "N/A")
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
        print("Used :", self._total)
        print("Trim :", _paper_size - self._total)
        print("\n")

    @property
    def output(self) -> DataFrame:
        return self._output

    @property
    def fitness_values(self) -> float:
        return self._fitness_values

    @property
    def total(self) -> float:
        return self._total

    @property
    def penalty(self) -> int:
        return self.penalty_calculator.penalty

    @penalty.setter
    def penalty(self, penalty: int) -> None:
        self.penalty_calculator.penalty = penalty
        
    @property
    def penalty_list(self) -> List:
        return self.penalty_calculator.penalty_list

    @penalty_list.setter
    def penalty_list(self, penalty_list: List) -> None:
        self.penalty_calculator.penalty_list = penalty_list

    @property
    def trim(self) -> float:
        return self._trim

    @property
    def PAPER_SIZE(self) -> float:
        return self._paper_size

    @PAPER_SIZE.setter
    def PAPER_SIZE(self, size: float):
        self._paper_size = size


def main():
    """Test the GA module with sampledata.csv"""
    import pandas as pd
    from pathlib import Path
    
    # Load sample data
    data_path = Path(__file__).parent.parent / 'data' / 'sampledata.csv'
    orders = pd.read_csv(data_path)
    
    # Initialize GA with default parameters
    ga = GA(
        orders=orders,
        size=66,
        showOutput=True,
    )
    
    # Run the genetic algorithm
    ga.run()
    
    # Print results
    print("\nFinal Results:")
    print(f"Best fitness value: {ga.fitness_values}")
    print(f"Total width used: {ga.total}")
    print(f"Paper size: {ga.PAPER_SIZE}")
    print("Trim :", ga.PAPER_SIZE - ga.total)
    print(f"Penalty: {ga.penalty}")
    print(f"Penalty list: {ga.penalty_list}")
   
    # Show output DataFrame
    with pd.option_context(
        'display.max_columns', None,
        'display.width', None,
        'display.colheader_justify', 'left'
    ):
        print("\nOutput DataFrame:")
        print(ga.output.drop(columns=['id', 'deadline', 'left_line','right_line','center_line']).to_string(index=False))


if __name__ == "__main__":
    main()

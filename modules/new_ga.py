from rules import Logic

import pygad as pg
import numpy as np
import pandas as pd
from typing import Callable, Optional

PENALTY_VALUE = 1000

class GA:
    def __init__(self, 
                 orders: pd.DataFrame,
                 size: float = 66,
                 num_generations: int = 100,
                 out_range: int = 6,
                 blade: Optional[int] = None,
                 seed: Optional[int] = None,
                 common: bool = False,
                 showOutput: bool = False,
                 showZero: bool = False):
        self.orders = orders
        self.size = size
        self.num_generations = num_generations
        self.out_range = out_range
        self.blade = blade
        self.seed = seed
        self.common = common
        
        # Internal state
        self._paper_size = int(size)
        self._penalty = 0
        self._penalty_value = PENALTY_VALUE
        self._total = 0
        self.current_generation = 0
        
        # Configuration defaults
        self.selector = None
        self.set_progress = None
        self.showOutput = False
        self.save_solutions = False
        self.showZero = False

        if orders is None:
            raise ValueError("Orders is empty!")
        
        self.model = pg.GA(
            num_generations=num_generations,
            num_parents_mating=60,
            fitness_func=self.fitness_function,
            sol_per_pop=120,
            num_genes=len(orders),
            gene_type=int,
            init_range_low=0,
            init_range_high=out_range,
            parent_selection_type="tournament",
            crossover_type="uniform",
            mutation_type="adaptive",
            mutation_probability=[0.25, 0.05],
            mutation_percent_genes=[25, 5],
            crossover_probability=0.75,
            on_generation=self.on_gen,
            on_stop=self.on_stop,
            save_solutions=False,
            stop_criteria="saturate_5",
            suppress_warnings=True,
            random_seed=seed,
        )

    def fitness_function(self, ga_instance, solution, solution_idx):
        self._penalty = 0
        self.Logic = Logic(self.orders, self.selector, self.common, self._paper_size, self.blade)
        
        if not self.size or not self._paper_size:
            # self._paper_size = random.sample(ROLL_PAPER, 1)[0]
            # self._paper_size = numpy.min(ROLL_PAPER)
            self._paper_size = 75

        self.Logic.paper_type_logic(solution)
        print('type logic',self.Logic.get_penalty())
        self.Logic.paper_out_logic(solution)
        print('out logic',self.Logic.get_penalty())
        self.Logic.paper_len_logic(solution)
        print('len logic',self.Logic.get_penalty())
        self.Logic.least_order_logic(solution)
        print('least logic',self.Logic.get_penalty())
        self.Logic.common_out_logic(solution)
        print('common logic',self.Logic.get_penalty())

        print('solution =',solution)
        _output = np.sum(solution * self.orders["width"])
        self.Logic.paper_size_logic(_output)
        print('size logic',self.Logic.get_penalty())
        
        print('---------------')
        trim = self._paper_size - _output
        print('trim =',trim)
        print('paper =',self._paper_size)
        print('output =',_output)
        self.Logic.paper_trim_logic(trim)
        print('trim logic',self.Logic.get_penalty())

        self._penalty = self.Logic.get_penalty()
        print('---------------')
        print('---------------')

        # Calculate base fitness focused on trim optimization
        base_fitness = trim  # Equivalent to (self._paper_size - _output)
        
        # Apply constraints as separate penalty
        return trim - self._penalty  # Penalize deviation from ideal 2

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

if __name__ == "__main__":
    # Sample valid test data
    # sample_orders = pd.DataFrame({
    #     'id': [1, 2, 3, 4],
    #     'order_number': ['A100', 'A101', 'B200', 'C300'],
    #     'quantity': [50, 60, 75, 40],
    #     'width': [10.5, 12.0, 9.8, 11.2],
    #     'edge_type': ['X', 'X', 'Y', 'Z'],
    #     'length': [100, 120, 90, 110],
    #     'component_type': ['front', 'back', 'middle', 'special'],
    #     'due_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
    #     'front_sheet': [1, 0, 0, 1],
    #     'c_wave': [0, 1, 1, 0],
    #     'middle_sheet': [0, 0, 1, 0],
    #     'b_wave': [0, 1, 0, 1],
    #     'back_sheet': [0, 1, 1, 0],
    #     'level': [2, 2, 3, 1],
    #     'left_edge_cut': [0, 0, 1, 0],
    #     'middle_edge_cut': [1, 1, 0, 1],
    #     'right_edge_cut': [0, 0, 1, 1]
    # })
    # Read and process sample orders with improved robustness and performance
    sample_orders = (
        pd.read_csv(
            '../data/cleaned_plan2024.csv',
            dtype={'width': float},  # Ensure numeric type for sorting
            usecols=['width'] + [col for col in pd.read_csv('../data/cleaned_plan2024.csv', nrows=0).columns]  # Read all columns
        )
        .sort_values(by='width', ascending=True)  # Explicit sort by column
        .head(100)  # Take top 100 narrowest orders
        .reset_index(drop=True)  # Clean index after sorting
    )

    ga_instance = GA(
        orders=sample_orders,
        size=66,
        #blade=1,
        common=True,
        showOutput=True,
        showZero=True,
    )
    ga_instance.run()

    print("\nTest Results:")
    print(f"Total trim: {ga_instance.fitness_values}")
    print(f"Penalty applied: {ga_instance.penalty}")
    print("Final output:\n", ga_instance.output)

from dataclasses import dataclass, field
from pandas import DataFrame
import pygad
import numpy
import pandas as pd
from typing import Callable, Dict, Any, List, Optional
from penalty import PenaltyCalculator
from trim import TrimCalculator, MAX_TRIM, MIN_TRIM

ROLL_PAPER = 66


@dataclass
class GA():
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
    parent_selection_type: str = "sss"
    crossover_type: str = "uniform"
    mutation_probability: Optional[List[float]] = field(
        default_factory=lambda: [0.25, 0.05]
    )
    mutation_percent_genes: Optional[List[int]] = field(default_factory=lambda: [25, 5])
    crossover_probability: Optional[float] = None
    common: Optional[bool] = False

    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.orders = self.orders[self.orders["quantity"] > 0].reset_index(drop=True)
        self._paper_size = int(self.size)
        self.penalty_calculator = PenaltyCalculator(self.orders, self.selector, self.common)
        self.trim_calculator = TrimCalculator()
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
            stop_criteria="saturate_7",
            suppress_warnings=True,
            random_seed=self.seed,
        )


    def fitness_function(self, ga_instance, solution, solution_idx):
        self.penalty_calculator.reset()
        if not self.size or not self._paper_size:
            self._paper_size = 75

        _output = numpy.sum(solution * self.orders["width"])
       
        # Calculate all penalties
        self.penalty_calculator.paper_type_logic(solution)
        self.penalty_calculator.paper_out_logic(solution)
        self.penalty_calculator.paper_len_logic(solution)
        self.penalty_calculator.least_order_logic(solution)
        self.penalty_calculator.common_out_logic(solution)
        self.penalty_calculator.paper_size_logic(_output, self._paper_size)
        
       # Calculate trim
        self._trim = self.trim_calculator.calculate_trim(self._paper_size, _output)
        trim_penalty = self.trim_calculator.apply_trim_penalty(self._trim)
        
        # Fitness is the trim value minus penalties
        fitness = self._trim - (self.penalty_calculator.penalty + trim_penalty)
        return fitness

    def on_gen(self, ga_instance):

        self.current_generation += 1
        if self.set_progress:
            progress = (self.current_generation / self.num_generations) * 100
            self.set_progress(progress)

    def on_stop(self, ga_instance, solution):

        orders = self.orders

        best_solution = ga_instance.best_solution()[0]
        
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

        out_array = numpy.array(_output["out"])
        width_array = numpy.array(_output["cut_width"])
        self._total = numpy.sum(out_array * width_array)
        self._fitness_values = ga_instance.best_solution()[1]
        self._output = _output

        if self.showOutput:
            self.show(ga_instance, _output)

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

    @property
    def run(self) -> Callable:
        return self.model.run


def main():
    """Test the GA module with sampledata.xlsx"""
    import pandas as pd
    from pathlib import Path
    
    # Load sample data
    data_path = Path(__file__).parent.parent / 'data' / 'sampledata.xlsx'
    orders = pd.read_excel(data_path)
    
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

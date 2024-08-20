from pandas import DataFrame
import pygad
import numpy
import pandas as pd
from typing import Callable, Dict, Any

from icecream import ic

from order_optimization.container import ModelInterface

MIN_TRIM = 1
PENALTY_VALUE = 1000



class GA(ModelInterface):
    def __init__(
        self,
        orders: DataFrame,
        size: float = 66,
        num_generations: int = 50,
        out_range: int = 6,
        showOutput: bool = False,
        save_solutions: bool = False,
        showZero: bool = False,
        selector: Dict[str, int] | None = None,
        set_progress: Callable | None = None
    ) -> None:
        self.orders = orders
        if orders.empty:
            raise ValueError("Orders is empty!")
        self._paper_size  = size
        self.selector = selector
        
        self._penalty = 0 
        self._penalty_value = PENALTY_VALUE


        self.showOutput = showOutput
        self.save_solutions = save_solutions
        self.showZero = showZero
        self.num_generations = num_generations

        self.num_parents_mating = 60
        self.sol_per_pop = 120
        self.num_genes = len(self.orders)

        self.init_range_low = 0
        self.init_range_high = out_range

        self.parent_selection_type = "tournament"
        self.crossover_type = "uniform"
        self.mutation_type = "random"
        self.mutation_percent_genes = 10
        self.gene_type = int
        self.current_generation = 0
        self.set_progress = set_progress

        self.model = pygad.GA(
            num_generations=self.num_generations,
            num_parents_mating=self.num_parents_mating,
            fitness_func=self.fitness_function,
            sol_per_pop=self.sol_per_pop,
            num_genes=self.num_genes,
            parent_selection_type=self.parent_selection_type,
            gene_type=self.gene_type,
            init_range_low=self.init_range_low,
            init_range_high=self.init_range_high,
            crossover_type=self.crossover_type,
            mutation_type=self.mutation_type,
            mutation_percent_genes=self.mutation_percent_genes,
            on_generation=self.on_gen,
            save_solutions=self.save_solutions,
        )

        
    def paper_type_logic(self, solution):
        init_type = None
        orders = self.orders
        match orders["ประเภททับเส้น"][self.get_first_solution(solution)]:
            case "X":
                init_type = 1
            case "N", "W":
                init_type = 2

        if init_type is not None:
            for index, out in enumerate(solution):
                if out >= 1:
                    match init_type:
                        case 1:
                            if orders["ประเภททับเส้น"][index] not in [
                                "X",
                                "Y",
                            ]:  # Changed OR to AND condition
                                self._penalty += self._penalty_value
                        case 2:
                            if orders["ประเภททับเส้น"][index] == "X":
                                self._penalty += self._penalty_value

    def least_order_logic(self, solution):
        init_order = None
        orders = self.orders

        init_order = orders["จำนวนสั่งขาย"][self.get_first_solution(solution)]

        for index, out in enumerate(solution):
            if out >= 1 and orders["จำนวนสั่งขาย"][index] < init_order:
                self._penalty += self._penalty_value

    def get_first_solution(self, solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def paper_out_logic(self, solution):
        if sum(solution) > 6:  # out รวมเกิน 6 = _penalty
            self._penalty += self._penalty_value * sum(solution)  # ยิ่งเกิน ยิ่ง _penaltyเยอะ
        order_length = 0
        for index, out in enumerate(solution):
            if out >= 1:
                order_length += 1
        if order_length > 2:
            self._penalty += self._penalty_value * order_length  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

    def paper_size_logic(self, _output):
        if _output > self._paper_size :  # ถ้าผลรวมมีค่ามากกว่า roll กำหนดขึ้น _penalty
            self._penalty += self._penalty_value * (
                _output - self._paper_size 
            )  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

    def paper_trim_logic(self, _fitness_values):
        if abs(_fitness_values) <= MIN_TRIM:  # ถ้าผลรวมมีค่าน้อยกว่า _penalty > เงื่อนไขบริษัท
            self._penalty += self._penalty_value

    def fitness_function(self, ga_instance, solution, solution_idx):
        self._penalty = 0

        if self.selector:
            solution[0] = self.selector["out"]

        self.paper_type_logic(solution)

        self.least_order_logic(solution)

        self.paper_out_logic(solution)

        _output = numpy.sum(solution * self.orders["กว้างผลิต"])  # ผลรวมของตัดกว้างทั้งหมด
        self.paper_size_logic(_output)

        _fitness_values = -self._paper_size  + _output  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี
        self.paper_trim_logic(_fitness_values)
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
                "blade": orders.index+1,
                "order_number": orders["เลขที่ใบสั่งขาย"],
                "num_orders": orders["จำนวนสั่งขาย"],
                "order_type": orders["ชนิดส่วนประกอบ"],
                "cut_width": orders["กว้างผลิต"],
                "cut_len": orders["ยาวผลิต"],
                "type": orders["ประเภททับเส้น"],
                "deadline": orders["กำหนดส่ง"],
                "front_sheet": orders["แผ่นหน้า"],
                "c_wave": orders["ลอน C"],
                "middle_sheet": orders["แผ่นกลาง"],
                "b_wave": orders["ลอน B"],
                "back_sheet": orders["แผ่นหลัง"],
                "num_layers": orders["จน.ชั้น"],
                "left_line": orders["ทับเส้นซ้าย"],
                "center_line": orders["ทับเส้นกลาง"],
                "right_line": orders["ทับเส้นขวา"],
                "out": solution,
            }
        )

        if not self.showZero:
            _output = _output[_output["out"] >= 1]
        _output = _output.reset_index(drop=True)

        blade = []
        for idx in _output.index:
            blade.append({"blade": idx + 1})
        blade = pd.DataFrame(blade)

        
        _output = pd.concat([_output, blade], axis=1)


        self._fitness_values = ga_instance.best_solution()[1]
        self._output = _output

        if self.showOutput:
            self.show(ga_instance, _output)

    def show(self, ga_instance, _output):
        _paper_size  = self._paper_size 
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

        print("Roll :", _paper_size )
        print("Used :", _paper_size  + self._fitness_values)
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
    def penalty(self, penalty:int) -> None:
        self._penalty = penalty

    @property
    def PAPER_SIZE(self) -> float:
        return self._paper_size 

    @PAPER_SIZE.setter
    def PAPER_SIZE (self, size: float):
        self._paper_size  = size
    
    @property
    def run(self) -> Callable:
        return self.model.run
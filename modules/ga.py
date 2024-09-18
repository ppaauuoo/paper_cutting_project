<<<<<<< HEAD
import pygad
import numpy
import pandas as pd
from .ordplan import ORD
from typing import Dict
class GA:
    def __init__(self, orders: ORD, size: float, num_generations: int, out_range: int,showOutput:bool = False, save_solutions:bool = False, showZero: bool = False, selector: Dict = None)->None:
        self.orders = orders
        self.PAPER_SIZE = size
        self.showOutput = showOutput
        self.save_solutions = save_solutions
        self.showZero = showZero
        self.selector = selector

        self.num_generations = num_generations
        # num_parents_mating = len(orders)
        # self.num_parents_mating = int((orders['จำนวนสั่งขาย'].median()/100 + size/100)/2)
        self.num_parents_mating = 60

        # sol_per_pop = len(orders)*2
        # self.sol_per_pop =  int(orders['จำนวนสั่งขาย'].median()/100 + size/100)
        self.sol_per_pop = 120
        self.num_genes = len(self.orders)

        self.init_range_low = 0
        self.init_range_high = out_range
        # self.init_range_high = abs(int(orders['จำนวนสั่งขาย'].median()/100 + size/100 - len(orders)*tuning_parameters))

        self.parent_selection_type = "tournament"
        # rws (for roulette wheel selection)
        # rank (for rank selection)
        # tournament (for tournament selection) - the best
        # sus (chat suggestion, stochastic_universal_selection)

        # crossover_type = "two_points"
        self.crossover_type = "uniform"  # - the best
        # crossover_type = "single_point"

        self.mutation_type = "random"
        self.mutation_percent_genes = 10
        # mutation_type = "adaptive"
        # mutation_percent_genes = (10,20)
        self.gene_type = int

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
            save_solutions=self.save_solutions
        )

        self.current_generation = 0
=======
from django.conf import settings

from dataclasses import dataclass
from pandas import DataFrame
import pygad
import numpy
import pandas as pd
from typing import Callable, Dict, Any, List, Optional
from icecream import ic

from order_optimization.container import ModelInterface

from ordplan_project.settings import MIN_TRIM,PENALTY_VALUE


@dataclass
class GA(ModelInterface):
    orders: DataFrame
    size: float = 66
    num_generations: int = 50
    out_range: int = 6
    showOutput: bool = False
    save_solutions: bool = False
    showZero: bool = False
    selector: Dict[str, Any] | None = None
    set_progress: Callable | None = None
    current_generation: int = 0
    _penalty:int = 0 
    _penalty_value:int = PENALTY_VALUE
    blade:Optional[int] = None
    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.orders = self.orders[self.orders['quantity'] > 0].reset_index(drop=True)
        self._paper_size  = self.size

        self.model = pygad.GA(
            num_generations=self.num_generations,
            num_parents_mating=60,
            fitness_func=self.fitness_function,
            sol_per_pop=120,
            num_genes=len(self.orders),
            parent_selection_type="tournament",
            gene_type=int,
            init_range_low=0,
            init_range_high=self.out_range,
            crossover_type="uniform",
            mutation_type="random",
            mutation_percent_genes=10,
            on_generation=self.on_gen,
            save_solutions=self.save_solutions,
        )

>>>>>>> develop
        
    def paper_type_logic(self, solution):
        init_type = None
        orders = self.orders
<<<<<<< HEAD
        for i, var in enumerate(solution):
            if init_type is not None:
                break
            if var >= 1:
                match orders['ประเภททับเส้น'][i]:
                    case "X":
                        init_type = 1
                    case "N", "W":
                        init_type = 2

        if init_type is not None:
            for i, var in enumerate(solution):
                if var >= 1:
                    match init_type:
                        case 1:
                            if orders['ประเภททับเส้น'][i] not in ["X", "Y"]:  # Changed OR to AND condition
                                self.penalty += self.penalty_value
                        case 2:
                            if orders['ประเภททับเส้น'][i] == "X":
                                self.penalty += self.penalty_value


    def least_order_logic(self, solution):
        init_type = None
        orders = self.orders
        for i, var in enumerate(solution):
            if init_type is not None:
                break
            if var >= 1:
                init_type = orders['จำนวนสั่งขาย'][i]

        if init_type is not None:
            for i, var in enumerate(solution):
                if var >= 1 and orders['จำนวนสั่งขาย'][i] < init_type:
                    self.penalty += self.penalty_value

    def paper_out_logic(self, solution):
        if sum(solution) > 6:  # 
            self.penalty += self.penalty_value*sum(solution)

        order_length = 0
        for i, var in enumerate(solution):
            if var >= 1:
                order_length+=1
        if order_length > 2:
            self.penalty += self.penalty_value*order_length

    def paper_size_logic(self,output):
        if output > self.PAPER_SIZE:  # ถ้าผลรวมมีค่ามากกว่า roll กำหนดขึ้น penalty
            self.penalty += self.penalty_value

    def paper_trim_logic(self,fitness_values):
        if abs(fitness_values) <= 1.22:  # ถ้าผลรวมมีค่าน้อยกว่า 1.22 penalty > เงื่อนไขบริษัท
            self.penalty += self.penalty_value

    def fitness_function(self, ga_instance, solution, solution_idx):
        self.penalty = 0
        self.penalty_value = 1000

        if self.selector:
            solution[0]=self.selector['out']

=======
        match orders["edge_type"][self.get_first_solution(solution)]:
            case "X":
                init_type = 1
            case "N":
                init_type = 2
            case "W":
                init_type = 2

        if init_type is not None:
            for index, out in enumerate(solution):
                if out >= 1:
                    match init_type:
                        case 1:
                            if orders["edge_type"][index] not in [
                                "X",
                                "Y",
                            ]:  # Changed OR to AND condition
                                self._penalty += self._penalty_value
                        case 2:
                            if orders["edge_type"][index] == "X":
                                self._penalty += self._penalty_value

    def least_order_logic(self, solution):
        init_order = None
        orders = self.orders

        init_order = orders["quantity"][self.get_first_solution(solution)]

        for index, out in enumerate(solution):
            if out >= 1 and orders["quantity"][index] < init_order:
                self._penalty += self._penalty_value

    @staticmethod
    def get_first_solution(solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def paper_out_logic(self, solution):
        if sum(solution) > 5:
            if sum(solution) <= 6:
                init = 0
                for index, out in enumerate(solution):
                    if out>=1:
                        if self.orders['edge_type'][index]=='X' and init==0:
                            init = 1
                            continue
                        if self.orders['edge_type'][index]=='Y' and init==1:
                            return                
            
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

    def selector_logic(self, solution: List[int])->List[int]:
        if self.selector is None:
            return solution
        
        try:
            solution[0] = self.selector["out"] #lock the first to be out (the first order is also the selector, manage by ORD)
        except KeyError:
            pass

        if solution[0] == 0: 
            solution[0] += 1

        return solution

    def fitness_function(self, ga_instance, solution, solution_idx):
        self._penalty = 0

        solution = self.selector_logic(solution)
>>>>>>> develop

        self.paper_type_logic(solution)

        self.least_order_logic(solution)

        self.paper_out_logic(solution)

<<<<<<< HEAD
        output = numpy.sum(solution * self.orders["กว้างผลิต"])  # ผลรวมของตัดกว้างทั้งหมด
        self.paper_size_logic(output)

        fitness_values = -self.PAPER_SIZE + output  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี
        self.paper_trim_logic(fitness_values)

        return fitness_values - self.penalty  # ลบด้วย penalty
=======
        _output = numpy.sum(solution * self.orders["width"])  # ผลรวมของตัดกว้างทั้งหมด
        self.paper_size_logic(_output)

        _fitness_values = -self._paper_size  + _output  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี
        self.paper_trim_logic(_fitness_values)
        return _fitness_values - self._penalty  # ลบด้วย _penalty
>>>>>>> develop

    def on_gen(self, ga_instance):

        self.current_generation += 1
        if self.set_progress:
<<<<<<< HEAD
                progress = (self.current_generation / self.num_generations) * 100
                self.set_progress(progress)
=======
            progress = (self.current_generation / self.num_generations) * 100
            self.set_progress(progress)
>>>>>>> develop

        orders = self.orders

        solution = ga_instance.best_solution()[0]

<<<<<<< HEAD
        output = pd.DataFrame(
            {
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
=======
        _output = pd.DataFrame(
            {   
                "id": orders['id'].unique(),
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
>>>>>>> develop
                "out": solution,
            }
        )

        if not self.showZero:
<<<<<<< HEAD
            output = output[output["out"] >= 1]
        output = output.reset_index(drop=True)

        self.fitness_values = ga_instance.best_solution()[1]
        self.output = output

        if self.showOutput:
            self.show(ga_instance, output)

    def show(self, ga_instance, output):
        PAPER_SIZE = self.PAPER_SIZE
=======
            _output = _output[_output["out"] >= 1]
        _output = _output.reset_index(drop=True)


        _output = self.blade_logic(_output)

        self._fitness_values = ga_instance.best_solution()[1]
        self._output = _output

        if self.showOutput:
            self.show(ga_instance, _output)

    def blade_logic(self, output: DataFrame) -> DataFrame:
        blade_list: List[Dict[str,int]] = []
        for idx in output.index:
            blade_val = idx+1
            if self.blade is not None:
                blade_val = self.blade
            blade_list.append({"blade": blade_val})

        blade_df = pd.DataFrame(blade_list)
        output = pd.concat([output, blade_df], axis=1)
        return output

    def show(self, ga_instance, _output):
        _paper_size  = self._paper_size 
>>>>>>> develop
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
<<<<<<< HEAD
            print(output.to_string(index=False))

        print("Roll :", PAPER_SIZE)
        print("Used :", PAPER_SIZE + self.fitness_values)
        print("Trim :", abs(self.fitness_values))
        print("\n")

    def get(self, set_progress):
        self.set_progress= set_progress
        return self.model
=======
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
>>>>>>> develop

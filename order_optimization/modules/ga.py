from pandas import DataFrame
import pygad
import numpy
import pandas as pd
from typing import Dict, Any

from icecream import ic

MIN_TRIM = 1
PENALTY_VALUE = 1000



class GA:
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
    ) -> None:
        self.orders = orders
        self.PAPER_SIZE = size
        self.selector = selector
        
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
                                self.penalty += self.penalty_value
                        case 2:
                            if orders["ประเภททับเส้น"][index] == "X":
                                self.penalty += self.penalty_value

    def least_order_logic(self, solution):
        init_order = None
        orders = self.orders

        init_order = orders["จำนวนสั่งขาย"][self.get_first_solution(solution)]

        for index, out in enumerate(solution):
            if out >= 1 and orders["จำนวนสั่งขาย"][index] < init_order:
                self.penalty += self.penalty_value

    def get_first_solution(self, solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def paper_out_logic(self, solution):
        if sum(solution) > 6:  # out รวมเกิน 6 = penalty
            self.penalty += self.penalty_value * sum(solution)  # ยิ่งเกิน ยิ่ง penaltyเยอะ
        order_length = 0
        for index, out in enumerate(solution):
            if out >= 1:
                order_length += 1
        if order_length > 2:
            self.penalty += self.penalty_value * order_length  # ยิ่งเกิน ยิ่ง penaltyเยอะ

    def paper_size_logic(self, output):
        if output > self.PAPER_SIZE:  # ถ้าผลรวมมีค่ามากกว่า roll กำหนดขึ้น penalty
            self.penalty += self.penalty_value * (
                output - self.PAPER_SIZE
            )  # ยิ่งเกิน ยิ่ง penaltyเยอะ

    def paper_trim_logic(self, fitness_values):
        if abs(fitness_values) <= MIN_TRIM:  # ถ้าผลรวมมีค่าน้อยกว่า penalty > เงื่อนไขบริษัท
            self.penalty += self.penalty_value * abs(
                fitness_values
            )  # ยิ่งเกิน ยิ่ง penaltyเยอะ

    def fitness_function(self, ga_instance, solution, solution_idx):
        self.penalty = 0
        self.penalty_value = PENALTY_VALUE

        if self.selector:
            solution[0] = self.selector["out"]

        self.paper_type_logic(solution)

        self.least_order_logic(solution)

        self.paper_out_logic(solution)

        output = numpy.sum(solution * self.orders["กว้างผลิต"])  # ผลรวมของตัดกว้างทั้งหมด
        self.paper_size_logic(output)

        fitness_values = -self.PAPER_SIZE + output  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี
        self.paper_trim_logic(fitness_values)
        return fitness_values - self.penalty  # ลบด้วย penalty

    def on_gen(self, ga_instance):

        self.current_generation += 1
        if self.set_progress:
            progress = (self.current_generation / self.num_generations) * 100
            self.set_progress(progress)

        orders = self.orders

        solution = ga_instance.best_solution()[0]

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
                "out": solution,
            }
        )

        if not self.showZero:
            output = output[output["out"] >= 1]
        output = output.reset_index(drop=True)

        self.fitness_values = ga_instance.best_solution()[1]
        self.output = output

        if self.showOutput:
            self.show(ga_instance, output)

    def show(self, ga_instance, output):
        PAPER_SIZE = self.PAPER_SIZE
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
            print(output.to_string(index=False))

        print("Roll :", PAPER_SIZE)
        print("Used :", PAPER_SIZE + self.fitness_values)
        print("Trim :", abs(self.fitness_values))
        print("\n")

    def get(self, set_progress):
        self.set_progress = set_progress
        return self.model

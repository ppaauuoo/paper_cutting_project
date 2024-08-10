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
        
    def paper_type_logic(self, solution):
        init_type = None
        orders = self.orders
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

        self.paper_type_logic(solution)

        self.paper_out_logic(solution)



        output = numpy.sum(solution * self.orders["กว้างผลิต"])  # ผลรวมของตัดกว้างทั้งหมด
        self.paper_size_logic(output)

        fitness_values = -self.PAPER_SIZE + output  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี
        self.paper_trim_logic(fitness_values)

        return fitness_values - self.penalty  # ลบด้วย penalty

    def on_gen(self, ga_instance):

        self.current_generation += 1
        if self.update_progress:
                progress = (self.current_generation / self.num_generations) * 100
                self.update_progress(progress)

        orders = self.orders

        solution = ga_instance.best_solution()[0]

        output = pd.DataFrame(
            {
                "order_number": orders["เลขที่ใบสั่งขาย"],
                "num_orders": orders["จำนวนสั่งขาย"],
                "cut_width": orders["กว้างผลิต"],
                "cut_len": orders["ยาวผลิต"],
                "type": orders["ประเภททับเส้น"],
                "deadline": orders["กำหนดส่ง"],
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

    def get(self, update_progress):
        self.update_progress= update_progress
        return self.model
import pygad
import numpy
import pandas as pd
from .ordplan import ORD


class GA:
    def __init__(self, orders, size, tuning_values, num_generations, showOutput=None):
        self.orders = ORD.prep(orders, size, tuning_values)
        self.PAPER_SIZE = size
        self.showOutput = False if showOutput is None else showOutput
        # the bigger the lesser

        self.num_generations = num_generations
        # num_parents_mating = len(orders)
        # self.num_parents_mating = int((orders['จำนวนสั่งขาย'].median()/100 + size/100)/2)
        self.num_parents_mating = 60

        # sol_per_pop = len(orders)*2
        # self.sol_per_pop =  int(orders['จำนวนสั่งขาย'].median()/100 + size/100)
        self.sol_per_pop = 120
        self.num_genes = len(self.orders)

        # self.init_range_low = 1
        # self.init_range_high = 2
        # self.init_range_high = abs(int(orders['จำนวนสั่งขาย'].median()/100 + size/100 - len(orders)*tuning_parameters))

        self.parent_selection_type = "tournament"
        # rws (for roulette wheel selection)
        # rank (for rank selection)
        # tournament (for tournament selection) - the best

        # crossover_type = "two_points"
        self.crossover_type = "uniform"  # - the best
        # crossover_type = "single_point"

        self.mutation_type = "random"
        self.mutation_percent_genes = 10
        # mutation_type = "adaptive"
        # mutation_percent_genes = (10,20)
        self.gene_type = int

    def fitness_function(self, ga_instance, solution, solution_idx):
        penalty = 0
        orders = self.orders
        PAPER_SIZE = self.PAPER_SIZE

        for i, var in enumerate(solution):
            if var < 0:  # ถ้ามีค่าน้อยกว่า 0 penalty > กันติดลบ
                penalty += abs(PAPER_SIZE * 2)

        if sum(solution) > 6:  # ถ้าผลรวมมีค่ามากกว่า 6 penalty > outได้สูงสุด 6 out ต่อรอบ
            penalty += abs(PAPER_SIZE * 2)

        if solution[solution >= 1].size > 2:  # out สูงสุด 2 ครั้ง ต่อออร์เดอร์
            penalty += abs(PAPER_SIZE * 2)

        output = numpy.sum(solution * orders["ตัดกว้าง"])  # ผลรวมของตัดกว้างทั้งหมด

        if output > PAPER_SIZE:  # ถ้าผลรวมมีค่ามากกว่า roll กำหนดขึ้น penalty
            penalty += abs(output * 2)

        fitness_values = -PAPER_SIZE + output  # ผลต่างของกระดาษที่มีกับออเดอร์ ยิ่งเยอะยิ่งดี

        if abs(fitness_values) <= 1.22:  # ถ้าผลรวมมีค่าน้อยกว่า 1.22 penalty > เงื่อนไขบริษัท
            penalty += abs(output * 2)

        return fitness_values - penalty  # ลบด้วย penalty

    def on_gen(self, ga_instance):
        orders = self.orders

        solution = ga_instance.best_solution()[0]

        output = pd.DataFrame(
            {
                "order_number": orders["เลขที่ใบสั่งขาย"],
                "num_layers": orders["จำนวนชั้น"],
                "cut_width": orders["ตัดกว้าง"],
                "out": solution,
            }
        )

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

    def get(self):
        return pygad.GA(
            num_generations=self.num_generations,
            num_parents_mating=self.num_parents_mating,
            fitness_func=self.fitness_function,
            sol_per_pop=self.sol_per_pop,
            num_genes=self.num_genes,
            parent_selection_type=self.parent_selection_type,
            gene_type=self.gene_type,
            # init_range_low=self.init_range_low,
            # init_range_high=self.init_range_high,
            crossover_type=self.crossover_type,
            mutation_type=self.mutation_type,
            mutation_percent_genes=self.mutation_percent_genes,
            on_generation=self.on_gen,
        )

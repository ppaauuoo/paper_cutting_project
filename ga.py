import pygad
import numpy
import pandas as pd
from ordplan import ORD

class GA:        
    def __init__(self,orders,size):
        self.orders = orders
        self.PAPER_SIZE = size
        tuning_parameters = 0.1
        #the bigger the lesser

        self.num_generations = int(len(orders)/(5*tuning_parameters))
        # num_parents_mating = len(orders)
        # self.num_parents_mating = int((orders['จำนวนสั่งขาย'].median()/100 + size/100)/2)
        self.num_parents_mating = 6
        
        # sol_per_pop = len(orders)*2
        # self.sol_per_pop =  int(orders['จำนวนสั่งขาย'].median()/100 + size/100)
        self.sol_per_pop =  12
        self.num_genes = len(orders)

        self.init_range_low = 3
        self.init_range_high = 3
        # self.init_range_high = abs(int(orders['จำนวนสั่งขาย'].median()/100 + size/100 - len(orders)*tuning_parameters))

        self.parent_selection_type = "tournament"
        #rws (for roulette wheel selection)
        #rank (for rank selection)
        #tournament (for tournament selection) - the best

        self.keep_parents = 1

        #crossover_type = "two_points" 
        self.crossover_type = "uniform" # - the best
        # crossover_type = "single_point"

        self.mutation_type = "random"
        self.mutation_percent_genes = 10
        # mutation_type = "adaptive"
        # mutation_percent_genes = (10,20)
        self.gene_type=int

    def check_roll_compat(self,var,i):
        orders = self.orders
        PAPER_SIZE = self.PAPER_SIZE
        if(var): #ถ้า var = 0 False
                if ORD.calculate_roll_and_width(PAPER_SIZE,2*orders.loc[i,'ตัดกว้าง']): #ถ้า width *2 แล้วผ่าน False
                    if ORD.calculate_roll_and_width(PAPER_SIZE,3*orders.loc[i,'ตัดกว้าง']): #ถ้า width *3 แล้วผ่าน False
                        if ORD.calculate_roll_and_width(PAPER_SIZE,4*orders.loc[i,'ตัดกว้าง']): #ถ้า width *4 แล้วผ่าน False
                            if ORD.calculate_roll_and_width(PAPER_SIZE,5*orders.loc[i,'ตัดกว้าง']): #ถ้า width *5 แล้วผ่าน False
                                if ORD.calculate_roll_and_width(PAPER_SIZE,6*orders.loc[i,'ตัดกว้าง']): #ถ้า width *6 แล้วผ่าน False ex. 4*6 = 24 > 22-24 = -2
                                    return abs(PAPER_SIZE*2)
        return 0
    
    def fitness_function(self,ga_instance, solution, solution_idx):
        penalty = 0
        orders = self.orders
        PAPER_SIZE = self.PAPER_SIZE
        for i,var in enumerate(solution):
            if var < 0: penalty+=abs(PAPER_SIZE*2)
            # if var % 2 and var!= 1: penalty+=abs(PAPER_SIZE*2)
            #penalty += check_roll_compat(var,i)

        if sum(solution) % 2: penalty+=abs(PAPER_SIZE*2)
            
        output = numpy.sum(solution*orders['ตัดกว้าง'])
        filter_solution = solution[solution >= 1]
        
        if len(filter_solution) > 2:
            penalty+=abs(output*2)
        if output > PAPER_SIZE: penalty+=abs(output*2)
        
        return -PAPER_SIZE + output - penalty

    def on_gen(self,ga_instance):
        orders = self.orders
        PAPER_SIZE = self.PAPER_SIZE
        print("Generation : ", ga_instance.generations_completed)
        print("Solution :")
        solution = ga_instance.best_solution()[0]


        output = pd.DataFrame({"cut_width": orders['ตัดกว้าง'], "out": solution})
        
        output = output[output["out"] >= 1]
        output = output.reset_index(drop=True)
        print(output)
        
        fitness_values = ga_instance.best_solution()[1]
        print("Roll :", PAPER_SIZE)
        print("Used :", PAPER_SIZE+fitness_values)
        print("Waste :", abs(fitness_values))
        print("\n")

    def get(self):
        return pygad.GA(num_generations=self.num_generations,
                        num_parents_mating=self.num_parents_mating,
                        fitness_func=self.fitness_function,
                        sol_per_pop=self.sol_per_pop,
                        num_genes=self.num_genes,
                        parent_selection_type = self.parent_selection_type,
                        keep_parents=self.keep_parents,
                        gene_type=self.gene_type,
                        init_range_low=self.init_range_low,
                        init_range_high=self.init_range_high,
                        crossover_type=self.crossover_type,
                        mutation_type=self.mutation_type,
                        mutation_percent_genes=self.mutation_percent_genes,
                        on_generation=self.on_gen)
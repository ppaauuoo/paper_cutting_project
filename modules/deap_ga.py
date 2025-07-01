from dataclasses import dataclass, field
from pandas import DataFrame
import numpy
import random
import pandas as pd
from typing import Callable, Dict, Any, List, Optional, Tuple
from deap import creator, base, tools
from penalty import PenaltyCalculator
from trim import TrimCalculator

ROLL_PAPER = 66

# สร้าง DEAP objects
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

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
    parent_selection_type: str = "sss" # ไม่ได้ใช้โดยตรงใน DEAP selTournament แต่เก็บไว้เป็น config
    crossover_type: str = "uniform" # ใช้โดย toolbox.register("mate", tools.cxUniform)
    mutation_probability: Optional[List[float]] = field(
        default_factory=lambda: [0.25, 0.05] # [prob_individual_mutated_start, prob_individual_mutated_end]
    )
    mutation_percent_genes: Optional[List[int]] = field(default_factory=lambda: [25, 5]) # [percent_genes_mutated_start, percent_genes_mutated_end]
    crossover_probability: Optional[float] = None # ความน่าจะเป็นที่ crossover จะเกิดขึ้น (ต่อคู่)
    common: Optional[bool] = False

    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.orders = self.orders[self.orders["quantity"] > 0].reset_index(drop=True)
        self._paper_size = int(self.size) if self.size else ROLL_PAPER
        self.penalty_calculator = PenaltyCalculator(self.orders, self.selector, self.common)
        self.trim_calculator = TrimCalculator()
        
        # ตั้งค่า DEAP toolbox
        self.toolbox = base.Toolbox()
        # ตั้งค่า seed สำหรับความสามารถในการทำซ้ำ
        if self.seed is not None:
            random.seed(self.seed)
            numpy.random.seed(self.seed)

        self.toolbox.register("attr_int", random.randint, 0, self.out_range-1)
        self.toolbox.register("individual", tools.initRepeat, creator.Individual, self.toolbox.attr_int, n=len(self.orders))
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.fitness_function)
        self.toolbox.register("mate", tools.cxUniform, indpb=0.5) # indpb คือความน่าจะเป็นที่แต่ละยีนจะถูกสลับในการทำ crossover
        self.toolbox.register("select", tools.selTournament, tournsize=3) # ใช้ Tournament Selection

    def fitness_function(self, individual):
        solution = individual
        self.penalty_calculator.reset()

        _output = numpy.sum(solution * self.orders["width"])
       
        # คำนวณค่าปรับทั้งหมด
        self.penalty_calculator.paper_type_logic(solution)
        self.penalty_calculator.paper_out_logic(solution)
        self.penalty_calculator.paper_len_logic(solution)
        self.penalty_calculator.least_order_logic(solution)
        self.penalty_calculator.common_out_logic(solution)
        self.penalty_calculator.paper_size_logic(_output, self._paper_size)
        
        # คำนวณค่า trim
        self._trim = self.trim_calculator.calculate_trim(self._paper_size, _output)
        trim_penalty = self.trim_calculator.apply_trim_penalty(self._trim)
        
        # fitness = trim - (penalty + trim_penalty)
        return (self._trim - (self.penalty_calculator.penalty + trim_penalty),)

    def run(self) -> None:
        population = self.toolbox.population(n=120)
        
        # ประเมิน fitness ของประชากรเริ่มต้น
        fitnesses = self.toolbox.map(self.toolbox.evaluate, population)
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        # กำหนด adaptive mutation parameters
        adaptive_params = {
            "mutation_probability": { # ความน่าจะเป็นที่แต่ละ individual จะถูก mutate
                0: self.mutation_probability[0],
                0.5: self.mutation_probability[1]
            },
            "mutation_percent_genes": { # เปอร์เซ็นต์ของยีนที่จะถูก mutate ภายใน individual นั้นๆ
                0: self.mutation_percent_genes[0],
                0.5: self.mutation_percent_genes[1]
            }
        }
        
        for gen in range(1, self.num_generations + 1):
            self.current_generation = gen # อัพเดท generation ปัจจุบัน

            # ปรับแต่งค่าพารามิเตอร์ mutation สำหรับ generation นี้
            ratio = gen / self.num_generations
            current_mut_prob_individual = self._get_adaptive_param(adaptive_params["mutation_probability"], ratio)
            current_mut_prob_gene = self._get_adaptive_param(adaptive_params["mutation_percent_genes"], ratio) / 100.0 # แปลงเปอร์เซ็นต์เป็นความน่าจะเป็น

            # เลือกวิวัฒนาการ (Selection for next generation's parents)
            offspring = self.toolbox.select(population, len(population)) # เลือก 120 individual สำหรับ mating pool
            offspring = list(map(self.toolbox.clone, offspring)) # โคลนเพื่อไม่ให้แก้ไขประชากรเดิม

            # Crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                # ใช้ crossover_probability ถ้ามีให้ หรือใช้ค่า default (เช่น 0.9)
                if random.random() < (self.crossover_probability if self.crossover_probability is not None else 0.9):
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values, child2.fitness.values
                
            # Mutation
            for mutant in offspring:
                if random.random() < current_mut_prob_individual: # ตรวจสอบว่า individual นี้ควรถูก mutate หรือไม่
                    # ใช้ mutUniformInt โดยที่แต่ละยีนมีความน่าจะเป็น current_mut_prob_gene ที่จะเปลี่ยน
                    tools.mutUniformInt(mutant, low=0, up=self.out_range-1, indpb=current_mut_prob_gene)
                    del mutant.fitness.values # ทำให้ fitness ไม่ถูกต้องหลังจากการ mutate
                
            # ประเมิน fitness ของ offspring ใหม่ (เฉพาะตัวที่ fitness ไม่ถูกต้อง)
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
                
            # อัพเดทประชากร (เช่น การแทนที่แบบ generational พร้อม elitism)
            # รวมประชากรปัจจุบันและ offspring แล้วเลือก 120 ตัวที่ดีที่สุด
            population[:] = self.toolbox.select(population + offspring, len(population))

            if self.set_progress:
                progress = (self.current_generation / self.num_generations) * 100
                self.set_progress(progress)

        best_ind = tools.selBest(population, 1)[0]
        self.on_stop(best_ind)

    def _get_adaptive_param(self, param_dict, ratio):
        keys = sorted(param_dict.keys())
        
        # จัดการกรณีขอบสำหรับ ratio
        if ratio <= keys[0]:
            return param_dict[keys[0]]
        if ratio >= keys[-1]:
            return param_dict[keys[-1]]

        lower_key = keys[0]
        upper_key = keys[-1]

        for i in range(len(keys) - 1):
            if keys[i] <= ratio < keys[i+1]:
                lower_key = keys[i]
                upper_key = keys[i+1]
                break
            
        lower_val = param_dict[lower_key]
        upper_val = param_dict[upper_key]
        
        # Interpolation (การประมาณค่าในช่วง)
        if lower_key != upper_key:
            fraction = (ratio - lower_key) / (upper_key - lower_key)
            return lower_val + (upper_val - lower_val) * fraction
        return lower_val

    def on_stop(self, solution): # เปลี่ยน signature ให้รับ best individual โดยตรง
        orders = self.orders

        best_solution = solution # ใช้ best individual ที่ส่งมาโดยตรง
        
        # สร้าง DataFrame ผลลัพธ์ที่มีจำนวนแถวที่สอดคล้องกัน
        output_data = {
            "id": orders["id"].values,
            "num_orders": orders["quantity"].values,
            "cut_width": orders["width"].values,
            "cut_len": orders["length"].values,
            "type": orders["edge_type"].values,
            "out": best_solution
        }
        
        # เพิ่มคอลัมน์เสริมถ้ามีอยู่ใน orders
        optional_cols = [
            "component_type", "due_date", "front_sheet", "c_wave",
            "middle_sheet", "b_wave", "back_sheet", "level",
            "left_edge_cut", "middle_edge_cut", "right_edge_cut"
        ]
        
        for col in optional_cols:
            if col in orders.columns:
                output_data[col] = orders[col].values
        
        _output = pd.DataFrame(output_data)
        
        # จัดการ order_number แยกต่างหากถ้ามี
        if 'order_number' in orders.columns:
            _output["order_number"] = orders["order_number"].values
            
        # เปลี่ยนชื่อคอลัมน์ให้ตรงกับรูปแบบผลลัพธ์ที่คาดหวัง
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
        self._fitness_values = solution.fitness.values[0] # ดึง fitness จาก best individual
        self._output = _output

        if self.showOutput:
            self.show(_output) # ลบพารามิเตอร์ ga_instance ออก

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

    def show(self, _output): # เปลี่ยน signature ให้รับ _output โดยตรง
        _paper_size = self._paper_size
        print("Generation : ", self.current_generation) # ใช้ self.current_generation
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

    # @property def run ถูกลบออกเนื่องจาก run เป็น method แล้ว

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
        seed=42 # เพิ่ม seed เพื่อความสามารถในการทำซ้ำ
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

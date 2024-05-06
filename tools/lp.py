import pandas as pd
from ortools.linear_solver import pywraplp

class LP:
    def __init__(self,orders,size):
        self.orders = orders
        self.PAPER_SIZE = size
    
    def run(self):
        orders = self.orders
        PAPER_SIZE = self.PAPER_SIZE
        output = {'PaperUsed':0,'PaperLeftOver':PAPER_SIZE,'OrderUsed':[]}
        solver = pywraplp.Solver.CreateSolver("SAT_INTEGER_PROGRAMMING")

        variables = {
            f"order_{i}": solver.IntVar(0, int(orders['จำนวนสั่งขาย'].median()/100 + PAPER_SIZE/100), f"order_{i}")
            for i, row in orders.iterrows()
        }

        solver.Add(sum(variables[f"order_{i}"] * row['ตัดกว้าง'] for i, row in orders.iterrows()) <= PAPER_SIZE)


        solver.Maximize(sum(variables[f"order_{i}"] * row['ตัดกว้าง'] for i, row in orders.iterrows()))

        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL: output["message"]=["No optimal solution found."]   

        paper_used = solver.Objective().Value()
        output["PaperUsed"] = f"{paper_used:0.1f}"
        output["PaperLeftOver"] = f"{PAPER_SIZE - paper_used:0.1f}"
        
        output["OrderUsed"] = [
        variables[f"order_{i}"].solution_value() 
        for i, row in orders.iterrows()
        ]
        self.output = output
        self.out()

    def out(self):
        output = self.output
        print("Solution :")
        solution = output["OrderUsed"]
        print(pd.DataFrame({"cut_width": self.orders['ตัดกว้าง'], "solution": solution}))   
        print("Used :", output["PaperUsed"])
        print("Waste :", output["PaperLeftOver"])
        print("\n")
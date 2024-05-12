import pandas as pd
from ortools.linear_solver import pywraplp
from ordplan import ORD
class LP:
    def __init__(self,orders,size,tuning_values):
        self.orders = ORD.prep(orders,size,tuning_values)
        self.PAPER_SIZE = size

    
    def run(self):
        PAPER_SIZE = self.PAPER_SIZE
        orders = self.orders
        output = {'PaperUsed':0,'PaperLeftOver':PAPER_SIZE,'OrderUsed':[]}
        solver = pywraplp.Solver.CreateSolver("SAT")

        variables = {
            f"order_{i}": solver.IntVar(0, 3, f"order_{i}")
            for i, row in orders.iterrows()
        }

        solver.Add(sum(variables[f"order_{i}"] * row['ตัดกว้าง'] for i, row in orders.iterrows()) <= PAPER_SIZE)
        solver.Add(PAPER_SIZE-sum(variables[f"order_{i}"] * row['ตัดกว้าง'] for i, row in orders.iterrows()) >= 1.2 )
        solver.Add(sum(variables[f"order_{i}"] for i, row in orders.iterrows())  <= 6)
        
        solver.Maximize(sum(variables[f"order_{i}"] * row['ตัดกว้าง'] for i, row in orders.iterrows()))

        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL: print("No optimal solution found.")   

        paper_used = solver.Objective().Value()
        output["PaperUsed"] = f"{paper_used:0.4f}"
        output["PaperLeftOver"] = f"{PAPER_SIZE - paper_used:0.4f}"
        order_values = []
    
        for i, row in orders.iterrows():
            order_values.append(variables[f"order_{i}"].solution_value())
        output["OrderUsed"] = list(order_values)
        self.output = output
        self.out()

    def out(self):
        output = self.output
        print("Solution :")
        solution = output["OrderUsed"]
        res = pd.DataFrame({"cut_width": self.orders['ตัดกว้าง'], "out": solution})
        
        res = res[res["out"] >= 1]
        res = res.reset_index(drop=True)
        print(res)
        print("Roll :", self.PAPER_SIZE)
        print("Used :", output["PaperUsed"])
        print("Waste :", output["PaperLeftOver"])
        print("\n")
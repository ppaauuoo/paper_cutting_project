<<<<<<< HEAD
import pandas as pd
from ortools.linear_solver import pywraplp
from .ordplan import ORD


class LP:
    def __init__(self, orders, size, tuning_values):
        self.orders = ORD.prep(orders, size, tuning_values)
        self.PAPER_SIZE = size

    def run(self):
        PAPER_SIZE = self.PAPER_SIZE
        orders = self.orders
        output = {"PaperUsed": 0, "PaperLeftOver": PAPER_SIZE, "OrderUsed": []}
        solver = pywraplp.Solver.CreateSolver("SAT")

        variables = {
            f"order_{i}": solver.IntVar(0, 3, f"order_{i}")
            for i, row in orders.iterrows()
        }

        solver.Add(
            sum(variables[f"order_{i}"] * row["ตัดกว้าง"] for i, row in orders.iterrows())
            <= PAPER_SIZE
        )
        solver.Add(
            PAPER_SIZE
            - sum(
                variables[f"order_{i}"] * row["ตัดกว้าง"] for i, row in orders.iterrows()
            )
            >= 1.2
        )
        solver.Add(sum(variables[f"order_{i}"] for i, row in orders.iterrows()) <= 6)

        solver.Maximize(
            sum(variables[f"order_{i}"] * row["ตัดกว้าง"] for i, row in orders.iterrows())
=======
from dataclasses import dataclass
from typing import Any, Dict
from numpy import roll
import pandas as pd

from ortools.linear_solver import pywraplp
# from ordplan_project.settings import ROLL_PAPER

ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]
@dataclass
class LP:
    results: Dict[str, Any]

    def run(self):
        roll_paper = ROLL_PAPER
        results = self.results
        if results is None:
            raise ValueError('Results is empty!')
        solver = pywraplp.Solver.CreateSolver("SAT")

        variables = {
            f'{roll}' :  solver.IntVar(0, 1,f'{roll}')
            for roll in roll_paper
        }

        solver.Add(
            sum(variables[f'{roll}'] for roll in roll_paper) <= 1
        )

        solver.Add(
            sum(roll * variables[f'{roll}'] for roll in roll_paper) - results['fitness'] <= 3
        )

        solver.Add(
            sum(roll * variables[f'{roll}'] for roll in roll_paper) - results['fitness'] >= 1
        )

        solver.Minimize(
             sum(roll * variables[f'{roll}'] for roll in roll_paper) - results['fitness']
>>>>>>> develop
        )

        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL:
<<<<<<< HEAD
            print("No optimal solution found.")

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
        res = pd.DataFrame({"cut_width": self.orders["ตัดกว้าง"], "out": solution})

        res = res[res["out"] >= 1]
        res = res.reset_index(drop=True)
        print(res)
        print("Roll :", self.PAPER_SIZE)
        print("Used :", output["PaperUsed"])
        print("Trim :", output["PaperLeftOver"])
        print("\n")
=======
            self.output = None
            return self

        output = {'new_trim': float, 'old_fitness': float, 'new_roll':int}
        new_trim = solver.Objective().Value()

        output['new_trim']= new_trim
        output['old_fitness']= results['fitness']
        output['new_roll'] = sum(variables[f'{roll}'].solution_value()*roll for roll in roll_paper)
        self.output = output
        return self

    def get(self):
        return self.output


def main():
    results = {'fitness': 74}
    model = LP(results)
    model.run()
    print(model.get())

if __name__ == "__main__":
    main()
>>>>>>> develop

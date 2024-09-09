from dataclasses import dataclass
from typing import Any, Dict
from numpy import roll
import pandas as pd

from ortools.linear_solver import pywraplp
# from ordplan_project.settings import ROLL_PAPER

ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]
@dataclass
class LP:
    results: Dict[str,Any]
    
    def run(self):
        roll_paper = ROLL_PAPER
        results = self.results
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
        )

        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL:
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
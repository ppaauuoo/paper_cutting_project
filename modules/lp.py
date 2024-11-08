from dataclasses import dataclass
from typing import Any, Dict

from ortools.linear_solver import pywraplp

from ordplan_project.settings import ROLL_PAPER


@dataclass
class LP:
    results: Dict[str, Any]

    def run(self):
        roll_paper = ROLL_PAPER
        results = self.results
        if results is None:
            raise ValueError("Results is empty!")
        solver = pywraplp.Solver.CreateSolver("SAT")

        variables = {f"{roll}": solver.IntVar(
            0, 1, f"{roll}") for roll in roll_paper}

        solver.Add(sum(variables[f"{roll}"] for roll in roll_paper) <= 1)

        solver.Add(
            sum(roll * variables[f"{roll}"]
                for roll in roll_paper) - results["total"]
            <= 3
        )

        solver.Add(
            sum(roll * variables[f"{roll}"]
                for roll in roll_paper) - results["total"]
            >= 1
        )

        solver.Minimize(
            sum(roll * variables[f"{roll}"]
                for roll in roll_paper) - results["total"]
        )

        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL:
            self.output = None
            return self

        output = {"new_trim": float, "new_roll": int}
        new_trim = solver.Objective().Value()

        output["new_trim"] = new_trim
        output["new_roll"] = sum(
            variables[f"{roll}"].solution_value() * roll for roll in roll_paper
        )
        self.output = output
        return self

    def get(self):
        return self.output


def main():
    results = {"total": 74}
    model = LP(results)
    model.run()
    print(model.get())


if __name__ == "__main__":
    main()

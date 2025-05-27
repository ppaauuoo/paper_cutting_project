from typing import List, Dict
import pandas as pd

MIN_TRIM = 1


class Logic:
    def __init__(self, orders):
        self.order = orders

    def paper_type_logic(self, solution):
        init_type = None
        orders = self.orders
        match orders["edge_type"][self.get_first_solution(solution)]:
            case "X":
                init_type = 1
            case "N":
                init_type = 2
            case "W":
                init_type = 2

        if init_type is not None:
            for index, out in enumerate(solution):
                if out >= 1:
                    match init_type:
                        case 1:
                            if orders["edge_type"][index] not in [
                                "X",
                                "Y",
                            ]:  # Changed OR to AND condition
                                self._penalty += self._penalty_value
                        case 2:
                            if orders["edge_type"][index] == "X":
                                self._penalty += self._penalty_value

    def least_order_logic(self, solution):
        init_order = None
        orders = self.orders

        init_order = orders["quantity"][self.get_first_solution(solution)]

        for index, out in enumerate(solution):
            if out >= 1 and orders["quantity"][index] < init_order:
                self._penalty += self._penalty_value

    @staticmethod
    def get_first_solution(solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def paper_out_logic(self, solution):
        if sum(solution) > 5:
            if sum(solution) <= 6:
                init = 0
                for index, out in enumerate(solution):
                    if out >= 1:
                        if self.orders["edge_type"][index] == "X" and init == 0:
                            init = 1
                            continue
                        if self.orders["edge_type"][index] == "Y" and init == 1:
                            return

            self._penalty += self._penalty_value * sum(
                solution
            )  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

        order_length = 0
        for index, out in enumerate(solution):
            if out >= 1:
                order_length += 1
        if order_length > 2:
            self._penalty += self._penalty_value * order_length  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

    def paper_size_logic(self, _output):
        if _output > self._paper_size:  # ถ้าผลรวมมีค่ามากกว่า roll กำหนดขึ้น _penalty
            self._penalty += self._penalty_value * (
                _output - self._paper_size
            )  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

    def paper_trim_logic(self, _fitness_values):
        if abs(_fitness_values) <= MIN_TRIM:  # ถ้าผลรวมมีค่าน้อยกว่า _penalty > เงื่อนไขบริษัท
            self._penalty += self._penalty_value

    def selector_logic(self, solution: List[int]) -> List[int]:
        if self.selector is None:
            return solution

        try:
            solution[0] = self.selector[
                "out"
            ]  # lock the first to be out (the first order is also the selector, manage by ORD)
        except KeyError:
            pass

        if solution[0] == 0:
            solution[0] += 1

        return solution

    def blade_logic(self, output: pd.DataFrame) -> pd.DataFrame:
        blade_list: List[Dict[str, int]] = []
        for idx in output.index:
            blade_val = idx + 1
            if self.blade is not None:
                blade_val = self.blade
            blade_list.append({"blade": blade_val})

        blade_df = pd.DataFrame(blade_list)
        output = pd.concat([output, blade_df], axis=1)
        return output

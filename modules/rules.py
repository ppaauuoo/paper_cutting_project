from typing import List, Dict
import pandas as pd

MIN_TRIM = 1
MAX_TRIM = 3


class Logic:
    def __init__(self, orders, selector, common, paper_size, blade):
        self.orders = orders
        self.selector = selector
        self._penalty_value = 1000
        self.common = common
        self._paper_size = paper_size
        self.blade = blade

    def paper_type_logic(self, solution):
        EDGE_TYPE = {"X": 1, "N": 2, "W": 2}

        first_index = self.get_first_solution(solution)
        init_type = EDGE_TYPE.get(self.orders["edge_type"][first_index], 0)
        if self.selector:
            init_type = EDGE_TYPE.get(self.selector["type"], 0)

        if not init_type:
            return

        for index, out in enumerate(solution):
            if out >= 1:
                edge_type = self.orders["edge_type"][index]
                if init_type == 1 and edge_type not in ["X", "Y"]:
                    self._penalty += self._penalty_value * 5
                if init_type == 2 and edge_type == "X":
                    self._penalty += self._penalty_value * 5

    def least_order_logic(self, solution):
        orders = self.orders

        init_quantity = orders["quantity"][self.get_first_solution(solution)]
        if self.selector:
            init_quantity = self.selector["num_orders"] / 2

        for index, out in enumerate(solution):
            if out >= 1 and orders["quantity"][index] < init_quantity:
                self._penalty += self._penalty_value

    @staticmethod
    def get_first_solution(solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def x_y_out_logic(self, solution, current_out):
        if current_out <= 6:
            orders = self.orders
            init = 0

            # if there is common init
            if self.selector:
                # if common init is not X return false
                if self.selector["type"] != "X":
                    return False
                init = 1

            for index, out in enumerate(solution):
                if out >= 1:
                    order_edge = orders["edge_type"][index]
                    # if no first order and not x return false
                    if order_edge != "X" and init == 0 and index == 0:
                        return False
                    # if no first order and is x set as first order
                    if order_edge == "X" and init == 0:
                        init = 1
                        continue
                    # if there was first order and is not y return false
                    if order_edge != "Y" and init == 1:
                        return False
            # if order <= 6 and is X and Y return true
            return True
        # if order > 6 return false
        return False

    def paper_len_logic(self, solution):
        order_length = 0
        for _, out in enumerate(solution):
            if out >= 1:
                order_length += 1
        if order_length > 2:
            self._penalty += self._penalty_value * order_length

    def paper_out_logic(self, solution):
        current_out = sum(solution)
        if self.selector:
            current_out += self.selector["out"]
        if current_out > 5:
            if self.x_y_out_logic(solution, current_out):
                return

            self._penalty += self._penalty_value * sum(
                solution
            )  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

    def paper_size_logic(self, _output):
        if not self.common:
            return
        if _output > self._paper_size:
            self._penalty += self._penalty_value * (
                _output - self._paper_size
            )  # ยิ่งเกิน ยิ่ง _penaltyเยอะ

    def paper_trim_logic(self, trim):
        if trim <= MIN_TRIM:
            self._penalty += self._penalty_value * abs(trim)
        if trim >= MAX_TRIM:
            self._penalty += self._penalty_value * trim

    def selector_logic(self, solution: List[int]) -> List[int]:
        if self.selector is None:
            return solution
        try:
            solution[0] = self.selector["out"]
        except KeyError:
            pass

        if solution[0] == 0:
            solution[0] += 1

        return solution

    def common_out_logic(self, solution: List[int]):
        if not self.common:
            return
        temp = 0
        for i in solution:
            temp += i
        if temp % 2 != 0:
            self._penalty += self._penalty_value * temp

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

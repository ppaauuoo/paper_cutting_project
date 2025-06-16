from typing import List, Dict, Any
from pandas import DataFrame
import numpy

PENALTY_VALUE = 1000

class PenaltyCalculator:
    def __init__(self, orders: DataFrame, selector: Dict[str, Any] = None, common: bool = False):
        self.orders = orders
        self.selector = selector
        self.common = common
        self._penalty = 0
        self._penalty_value = PENALTY_VALUE
        self._penalty_list = []

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
                    self._penalty_list.append('type')
                if init_type == 2 and edge_type == "X":
                    self._penalty += self._penalty_value * 5
                    self._penalty_list.append('type')

    def least_order_logic(self, solution):
        orders = self.orders
        init_quantity = orders["quantity"][self.get_first_solution(solution)]
        if self.selector:
            init_quantity = self.selector["num_orders"] / 2

        for index, out in enumerate(solution):
            if out >= 1 and orders["quantity"][index] < init_quantity:
                self._penalty += self._penalty_value
                self._penalty_list.append('least')

    def paper_len_logic(self, solution):
        order_length = 0
        for index, out in enumerate(solution):
            if out >= 1:
                order_length += 1
        if order_length > 2:
            self._penalty += self._penalty_value * order_length
            self._penalty_list.append('length')

    def paper_out_logic(self, solution):
        current_out = sum(solution)
        if self.selector:
            current_out += self.selector["out"]
        if current_out > 5:
            if not self.x_y_out_logic(solution, current_out):
                self._penalty += self._penalty_value * sum(solution)
                self._penalty_list.append('out')

    def paper_size_logic(self, _output, paper_size):
        if not self.common:
            return
        if _output > paper_size:
            self._penalty += self._penalty_value * (_output - paper_size)
            self._penalty_list.append('size')

    def common_out_logic(self, solution: List[int]):
        if not self.common:
            return
        temp = 0
        for i in solution:
            temp += i
        if temp % 2 != 0:
            self._penalty += self._penalty_value * temp
            self._penalty_list.append('common')

    def x_y_out_logic(self, solution, current_out):
        if current_out <= 6:
            orders = self.orders
            init = 0

            if self.selector:
                if self.selector["type"] != "X":
                    return False
                init = 1

            for index, out in enumerate(solution):
                if out >= 1:
                    order_edge = orders["edge_type"][index]
                    if order_edge != "X" and init == 0 and index == 0:
                        return False
                    if order_edge == "X" and init == 0:
                        init = 1
                        continue
                    if order_edge != "Y" and init == 1:
                        return False
            return True
        return False

    @staticmethod
    def get_first_solution(solution) -> int:
        for index, out in enumerate(solution):
            if out >= 1:
                return index
        return 0

    def reset(self):
        self._penalty_list = []
        self._penalty = 0

    @property
    def penalty(self) -> int:
        return self._penalty
    
    @penalty.setter
    def penalty(self, penalty: int) -> None:
        self._penalty = penalty
        
    @property
    def penalty_list(self) -> List:
        return self._penalty_list
    
    @penalty_list.setter
    def penalty_list(self, penalty_list: List) -> None:
        self._penalty_list = penalty_list

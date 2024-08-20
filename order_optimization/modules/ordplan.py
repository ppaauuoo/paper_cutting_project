import pandas as pd
from typing import Dict

from icecream import ic

from pandas import DataFrame

from order_optimization.container import ProviderInterface

MM_TO_INCH = 25.4

COMMON_FILTER = [
    "front_sheet",
    "c_wave",
    "middle_sheet",
    "b_wave",
    "back_sheet",
    "level",
    "edge_type",
    "width",
    "length",
    "left_edge_cut",
    "middle_edge_cut",
    "right_edge_cut",
    "component_type",
]


class ORD(ProviderInterface):
    def __init__(
        self,
        orders: DataFrame,
        deadline_scope: int = 0,
        size: float = 66,
        tuning_values: int = 3,
        filter_value: int = 16,
        _filter_diff: bool = True,
        common: bool = False,
        filler: int = 0,
        selector: Dict[str, int] | None = None,
        first_date_only: bool = False,
        no_build: bool = False,
        deadline_range: int = 50,
    ) -> None:
        if orders is None:
            raise ValueError("Orders is empty!")
        self.ordplan: DataFrame = orders
        self.deadline_scope = deadline_scope
        self._filter_diff = _filter_diff
        self.common = common
        self.size = size
        self.tuning_values = tuning_values
        self.filter_value = filter_value
        self.filler = filler
        self.selector = selector
        self.first_date_only = first_date_only
        self.deadline_range = deadline_range
        self.lookup_amount = 0
        if not no_build:
            self.build()

    def build(self) -> None:
        self.format_data()
        if self.first_date_only:
            self.set_first_date()
        else:
            self.expand_deadline_scope()
        self.filter_common_order()
        self.set_selected_order()

    def get(self) -> DataFrame:
        self.ordplan["due_date"] = self.ordplan["due_date"].dt.strftime("%m/%d/%y")
        return self.ordplan

    def set_first_date(self):
        ordplan = self.ordplan
        deadline = ordplan["due_date"].iloc[0]
        ordplan = ordplan[ordplan["due_date"] == deadline].reset_index(
            drop=True
        )  # filter only fist deadline
        self.lookup_amount = len(ordplan)
        self.ordplan = self.filter_diff_order(ordplan)

    def expand_deadline_scope(self):
        if self.deadline_scope < 0:
            self.lookup_amount = len(self.ordplan)
            self.ordplan = self.filter_diff_order(self.ordplan)
            return

        deadline_range = self.deadline_range
        deadlines = self.ordplan["due_date"].unique()

        for deadline in deadlines:
            deadline = pd.to_datetime(deadline, format="%m/%d/%y")
            ordplan = (
                self.ordplan[self.ordplan["due_date"] <= deadline]
                .sort_values("due_date")
                .reset_index(drop=True)
            )
            self.lookup_amount = len(ordplan)
            ordplan = self.filter_diff_order(ordplan)
            if len(ordplan) >= deadline_range:
                break
        self.ordplan = ordplan
        return

    def format_data(self):
        ordplan = self.ordplan
        ordplan["width"] = round(ordplan["width"] / MM_TO_INCH, 2)
        ordplan["length"] = round(ordplan["length"] / MM_TO_INCH, 2)
        ordplan["due_date"] = pd.to_datetime(ordplan["due_date"], format="%m/%d/%y")

        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA

        ordplan = ordplan[ordplan["length"] != 0]  # drop len = 0

        self.ordplan = ordplan

    def filter_diff_order(self, ordplan: DataFrame) -> DataFrame:
        if not self._filter_diff:
            return ordplan
        if ordplan is None:
            raise ValueError("Order is empty!")

        selected_values = self.size / self.tuning_values
        ordplan["diff"] = ordplan["width"].apply(
            lambda x: abs(selected_values - x)
        )  # add diff col
        ordplan = (
            ordplan[ordplan["diff"] < self.filter_value]
            .sort_values(by="width")
            .reset_index(drop=True)
        )  # filter out diff

        return ordplan

    def set_selected_order(self):
        if not self.selector:
            return
        self.selected_order = self.ordplan[
            self.ordplan["order_number"] == self.selector["order_id"]
        ]  # get selected orders
        ordplan = self.ordplan[
            self.ordplan["order_number"] != self.selector["order_id"]
        ]  # filter out selected orders
        self.ordplan = pd.concat(
            [self.selected_order, ordplan], ignore_index=True
        )  # add selected orders to the top row for GA

    def filter_common_order(self):
        if not self.common:
            return
        ordplan = self.ordplan
        init_order = self.ordplan.iloc[0]  # use first orders as init

        init_order = self.set_filler_order(init_order)

        common_cols = COMMON_FILTER
        mask = (
            ordplan[common_cols].eq(init_order[common_cols]).all(axis=1)
        )  # common mask
        self.ordplan = ordplan.loc[mask].reset_index(drop=True)  # filter out with mask

    def set_filler_order(self, init_order):
        if not self.filler:
            return init_order
        ordplan = self.ordplan
        init_order = ordplan[
            ordplan["order_number"] == self.filler
        ]  # use filler as init instead
        self.ordplan = ordplan[
            ordplan["order_number"] != self.filler
        ]  # remove dupe filler
        return init_order

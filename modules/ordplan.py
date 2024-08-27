from django.conf import settings

import pandas as pd
from typing import Dict, Any
from icecream import ic
from pandas import DataFrame
from dataclasses import dataclass

from order_optimization.container import ProviderInterface

UNIT_CONVERTER = settings.UNIT_CONVERTER
COMMON_FILTER = settings.COMMON_FILTER
DEADLINE_RANGE = settings.DEADLINE_RANGE

@dataclass
class ORD(ProviderInterface):
    orders: DataFrame
    deadline_scope: int = 0
    size: float = 66
    tuning_values: int = 3
    filter_value: int = 16
    _filter_diff: bool = True
    common: bool = False
    filler: int = 0
    selector: Dict[str, Any] | None = None
    first_date_only: bool = False
    no_build: bool = False
    deadline_range: int = DEADLINE_RANGE
    lookup_amount: int = 0

    def __post_init__(self):
        if self.orders is None:
            raise ValueError("Orders is empty!")
        self.ordplan: DataFrame = self.orders
        if not self.no_build:
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
        df = self.ordplan.copy()
        for column in df.columns:
            if df[column].dtype == 'datetime64[ns]':
                df[column] = df[column].dt.strftime("%m/%d/%y")
        return df

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
        ordplan["due_date"] = pd.to_datetime(ordplan["due_date"], format="%m/%d/%y")
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        ordplan = ordplan[ordplan["length"] > 0]  # drop len = 0
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
        if self.selector is None:
            return
        self.selected_order = self.ordplan[
            self.ordplan["id"] == self.selector["order_id"]
        ]  # get selected orders
        ordplan = self.ordplan[
            self.ordplan["id"] != self.selector["order_id"]
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
            ordplan["id"] == self.filler
        ]  # use filler as init instead
        self.ordplan = ordplan[
            ordplan["id"] != self.filler
        ]  # remove dupe filler
        return init_order

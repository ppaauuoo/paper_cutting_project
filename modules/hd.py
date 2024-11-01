from icecream import ic
from typing import Any, Optional, Dict
from dataclasses import dataclass
import pandas as pd
from order_optimization.container import ProviderInterface
from ordplan_project.settings import (
    PLAN_RANGE,
    LEGACY_FILTER,
    DEADLINE_RANGE,
    ROLL_PAPER,
    COMMON_FILTER
)
import random


@dataclass
class HD(ProviderInterface):
    orders: pd.DataFrame
    x: int = 10
    h_type: str = "ffa"
    start_date: Optional[pd.Timestamp] = None
    stop_date: Optional[pd.Timestamp] = None
    common: bool = False
    common_init_order: Optional[Dict[str, Any]] = None
    preview: bool = False

    is_build: bool = True

    def __post_init__(self):
        if self.orders.empty:
            raise ValueError("Orders Empty!")
        if self.is_build:
            self.build()

    def build(self):
        data = self.format_data(self.orders)
        data = self.date_range_limit(data)

        filters = {False: self.legacy_filter_order,
                   True: self.filter_common_order}
        post_data = filters.get(self.common)(data)
        self.temp_size = min(ROLL_PAPER)
        ff_list = []
        ffa_list = []
        ffd_list = []

        match (self.h_type):
            case "ff":
                ff_list = [[] for _ in range(self.x)]
                for item, id in zip(post_data["width"], post_data["id"]):
                    ff_list = self.first_fit(ff_list, item, id)
                data_df = self.df_formatter(ff_list)
            case "ffa":
                ffa_list = [[] for _ in range(self.x)]
                asc_p_data = post_data.sort_values("width", ascending=True)
                for item, id in zip(asc_p_data["width"], asc_p_data["id"]):
                    ffa_list = self.first_fit(ffa_list, item, id)
                data_df = self.df_formatter(ffa_list)
            # case "ffd":
                ffd_list = [[] for _ in range(round(self.x * 20 / 100))]
                dsc_p_data = post_data.sort_values("width", ascending=False)
                for item, id in zip(dsc_p_data["width"], dsc_p_data["id"]):
                    ffd_list = self.first_fit(ffd_list, item, id)
                # data_df = self.df_formatter(ffd_list)
                ffd_df = self.df_formatter(ffd_list)
                data_df = pd.concat([data_df, ffd_df], ignore_index=True)

        heuristic_data_id = data_df.drop_duplicates(
            "id").reset_index(drop=True)

        self.heuristic_data = post_data[
            post_data["id"].isin(heuristic_data_id["id"])
        ].reset_index(drop=True)

    @staticmethod
    def format_data(data):
        """Format due date for calculation purpose
        and filter out any unuseable data."""
        ordplan = data.copy()
        ordplan["due_date"] = pd.to_datetime(
            ordplan["due_date"], format="%m/%d/%Y")
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        ordplan = ordplan[ordplan["length"] > 0]  # drop len = 0
        ordplan = ordplan[ordplan["quantity"] > 500]  # drop quantity = 500

        return ordplan

    def is_fit(self, data_list, item):
        return sum([row[0] for row in data_list]) + item - self.temp_size < 0

    @staticmethod
    def get_width(data_list):
        return [row[0] for row in data_list]

    def width_sum_formatter(self, data_list):
        output = ""
        for index, _ in enumerate(data_list):
            output += str(
                round(sum(self.get_width(data_list[index])), 4)) + " | "
        return output

    @staticmethod
    def df_formatter(data_list):
        combined_data = []
        for data in data_list:
            combined_data += data
        return pd.DataFrame(combined_data, columns=["width", "id"])

    def first_fit(self, data_list, item, id):
        for data in data_list:
            if self.is_fit(data, item):
                data.append((item, id))
                return data_list
        return data_list

    def get(self) -> pd.DataFrame:
        return self.heuristic_data

    def date_range_limit(self, data):
        if self.stop_date and self.start_date:
            data = data[
                (data["due_date"] >= self.start_date)
                & (data["due_date"] <= self.stop_date)
            ].reset_index(drop=True)
        if len(data) < PLAN_RANGE:
            raise ValueError('No Orders in Date Range.')
        return data

    def legacy_filter_order(
        self,
        data,
        data_range: float = DEADLINE_RANGE,
        best_plan: pd.DataFrame = pd.DataFrame(None),
    ):
        used_data = data.head(int(data_range)).copy()

        leg_filters = LEGACY_FILTER
        indices = list(range(0, len(used_data)))
        random.shuffle(indices)
        indices = indices[:100]

        for index in indices:
            init_order = used_data.iloc[index]
            # Create a mask for matching orders using all legacy filters
            mask = (used_data[leg_filters].eq(
                init_order[leg_filters])).all(axis=1)
            # Apply the mask and reset the index
            plan = used_data.loc[mask].reset_index(drop=True)

            if len(plan) > len(best_plan):
                best_plan = plan
                return best_plan

            # early stop
            if len(best_plan) >= PLAN_RANGE:
                break

        # return best_plan

    def filter_common_order(self, data):
        """Use common filter base on the first order or filler order."""
        if not self.common:
            return

        filters = LEGACY_FILTER.copy()
        filters.append("length")

        init_order = pd.DataFrame([self.common_init_order])
        init_order.rename(columns={"cut_len": "length"}, inplace=True)
        if init_order is None:
            raise ValueError("Common init order is None!")
        mask = (data[filters].eq(init_order[filters].iloc[0])).all(axis=1)
        filtered_plan = data.loc[mask].reset_index(drop=True).copy()
        if len(filtered_plan) <= 0:
            raise ValueError("Common Not Found")
        best_plan = pd.DataFrame(None)
        indices = list(range(len(filtered_plan)))
        random.shuffle(indices)
        indices = indices[:100]
        common_filters = COMMON_FILTER
        for index in indices:
            init_order = filtered_plan.iloc[index]
            mask = (data[common_filters].eq(init_order[common_filters])).all(axis=1)
            orders = data.loc[mask].reset_index(drop=True).copy()

            if len(orders) > len(best_plan):
                best_plan = orders
                return best_plan

            # early stop
            if len(best_plan) >= PLAN_RANGE:
                break

        # return best_plan

import random
from django.conf import settings

import pandas as pd
from typing import Dict, Any, Optional
from icecream import ic
from pandas import DataFrame
from dataclasses import dataclass

from order_optimization.container import ProviderInterface
from ordplan_project.settings import PLAN_RANGE, LEGACY_FILTER,COMMON_FILTER,UNIT_CONVERTER,DEADLINE_RANGE

@dataclass
class ORD(ProviderInterface):
    """Raw orders processor.

    Args:
        orders: Raw orders dataframe.
        deadline_scope: -1 to scan all orders, 0 by default.
        size : Paper roll.
        tuning_values : Paper roll divider.
        filter_value : Acceptable orders range.
        _filter_diff : False to skip order's differences filter, True by default.
        common : True to use common filter, False by default.
        filler : Chosen order id to be the base for common filter.
        selector : A dict of a chosen order id with out for setting first order.
        first_date_only : True to filter only the latest due date.
        no_build : True to skip everything, use for testing.
        deadline_range : Range of orders.
        preview : True to skip all filter.
        start_date : Datetime of start date.
        stop_date : Datetime of stop date.
    """
    orders: DataFrame
    deadline_scope: int = 0
    size: float = 66
    tuning_values: int = 3
    filter_value: int = 16
    _filter_diff: bool = True
    common: bool = False
    filler: Optional[str] = None
    selector: Dict[str, Any] | None = None
    first_date_only: bool = False
    no_build: bool = False
    deadline_range: int = DEADLINE_RANGE
    lookup_amount: int = 0
    preview: bool = False
    start_date: Optional[pd.Timestamp] = None
    stop_date: Optional[pd.Timestamp] = None

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

        if self.common:
            self.filter_common_order()
        else:
            self.legacy_filter_order()
            
        self.order_limiter()
        self.set_selected_order()


    def get(self) -> DataFrame:
        """Processed orders getter
        Returns:
            Dataframe of processed orders.
        """
        df = self.ordplan.copy()
        for column in df.columns:
            if df[column].dtype == 'datetime64[ns]':
                df[column] = df[column].dt.strftime("%m/%d/%y")
        return df

    def order_limiter(self):
        """Cut orders to be in PLAN_RANGE."""
        if len(self.ordplan) <= PLAN_RANGE:
            return
        self.ordplan = self.ordplan.head(int(PLAN_RANGE)).copy()


    def set_first_date(self):
        """Filter only the latest due date."""
        ordplan = self.ordplan
        deadline = ordplan["due_date"].iloc[0]
        ordplan = ordplan[ordplan["due_date"] == deadline].reset_index(
            drop=True
        )  # filter only fist deadline
        self.lookup_amount = len(ordplan)
        self.ordplan = self.filter_diff_order(ordplan)

    def expand_deadline_scope(self):
        """Expands due date base from defined range."""
        
        # Exit early if deadline scope is negative
        if self.deadline_scope < 0:
            self.lookup_amount = len(self.ordplan)
            self.ordplan = self.filter_diff_order(self.ordplan)
            return
        
        # Convert due_date to datetime format for consistency
        self.ordplan["due_date"] = pd.to_datetime(self.ordplan["due_date"], format="%m/%d/%y")
        
        filtered_plan = self.ordplan.copy()

        # Filter plan by start and stop dates if provided
        if self.stop_date:
            filtered_plan = (
                self.ordplan[
                    (self.ordplan['due_date'] >= self.start_date) & 
                    (self.ordplan['due_date'] <= self.stop_date)
                ]
                .copy()
            )  # Create a copy to avoid modifying the original plan
        
        deadlines = filtered_plan["due_date"].unique()
        
        # Raise error if no data aligns with dates

        if len(deadlines) == 0:
            raise ValueError("No data aligns with date")
        
        ordplan = None
        for deadline in deadlines:

            filtered_ordplan = (
                filtered_plan[filtered_plan["due_date"] <= deadline]
                .sort_values("due_date")
                .reset_index(drop=True)
            )
            
   
            
            # Filter order differences and update lookup amount
            filtered_ordplan = self.filter_diff_order(filtered_ordplan)
            self.lookup_amount = len(filtered_ordplan)
            

            if len(filtered_ordplan) >= self.deadline_range*2:
                raise ValueError("Orders is exceeding!")

            # Update ordplan if the current deadline range is reached or exceeded
            if len(filtered_ordplan) >= self.deadline_range:
                self.ordplan = filtered_ordplan
                return
        
        # If no matching deadlines found, update ordplan with existing data
        self.ordplan = filtered_plan

    
    def format_data(self):
        """Format due date for calculation purpose and filter out any unuseable data."""
        ordplan = self.ordplan
        ordplan["due_date"] = pd.to_datetime(ordplan["due_date"], format="%m/%d/%y")
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        ordplan = ordplan[ordplan["length"] > 0]  # drop len = 0
        ordplan = ordplan[ordplan["quantity"] > 0]  # drop quantity = 0

        self.ordplan = ordplan

    def filter_diff_order(self, ordplan: DataFrame) -> DataFrame:
        """Assign order's differences base on roll paper,
        then filter out any unuse orders."""
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
            .reset_index(drop=True)
        )  # filter out diff

        return ordplan

    def set_selected_order(self):
        """Set selector order to be the first order for
        optimizing purpose."""
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
        """Use common filter base on the first order or filler order."""
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

    def legacy_filter_order(self):
        """Randomly choose an init order to be the base for
        legacy filter, then filter out data."""

        if self.preview:
            return
        legacy_filters = LEGACY_FILTER
        ordplan = pd.DataFrame(None)
        best_index=0
        most_compat_plan = 0
        indices = list(range(len(self.ordplan)))
        random.shuffle(indices)

        for index in indices:
            init_order = self.ordplan.iloc[index]
            # Create a mask for matching orders using all legacy filters
            mask = (self.ordplan[legacy_filters].eq(init_order[legacy_filters])).all(axis=1)
            # Apply the mask and reset the index
            ordplan = self.ordplan.loc[mask].reset_index(drop=True)
            if len(ordplan)>most_compat_plan:
                best_index=index
                most_compat_plan=len(ordplan)

        init_order = self.ordplan.iloc[best_index]
        mask = (self.ordplan[legacy_filters].eq(init_order[legacy_filters])).all(axis=1)
        ordplan = self.ordplan.loc[mask].reset_index(drop=True)

        self.ordplan = ordplan

    def set_filler_order(self, init_order):
        """Eject order data with the filler id."""
        if self.filler is None:
            return init_order
        init_order = self.ordplan[self.ordplan['id'] == self.filler].iloc[0]
        self.ordplan = self.ordplan[self.ordplan['id'] != self.filler]
        return init_order
                
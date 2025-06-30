from typing import Any, Dict, List

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime

from core.utils import timezone_formatter
from order_optimization.models import OptimizationPlan, OrderList, PlanOrder


def plan_orders_formatter() -> pd.DataFrame:
    """
    Request data from model and format it.
    This function remains Django-specific due to direct ORM queries.
    """

    # Get all PlanOrder objects as a list of dictionaries
    optimized_output = list(
        PlanOrder.objects.all().values(
            "order__id",
            "order__order_number",
            "blade_type",
            "paper_roll",
            "out",
            "plan_quantity",
            "order_leftover",
            "blade_1_orders__id",  # Correct reverse relation to OptimizationPlan
            "blade_2_orders__id",  # Correct reverse relation to OptimizationPlan
        )
    )

    # Extract original order IDs (from the related OrderList)
    optimized_output_ids = [item["order__id"] for item in optimized_output]

    # Get corresponding OrderList objects
    optimized_order_list = list(
        OrderList.objects.filter(id__in=optimized_output_ids).values(
            "id",
            "quantity",
            "width",
            "length",
            "edge_type",
            "due_date",
            "front_sheet",
            "c_wave",
            "middle_sheet",
            "b_wave",
            "back_sheet",
            "level",
            "left_edge_cut",
            "middle_edge_cut",
            "right_edge_cut",
            "component_type",
        )
    )

    # Create a dictionary with order_id as the key
    optimized_order_dict = {order["id"]: order
                            for order in optimized_order_list}

    # Combine results
    combined_results = []
    for plan_order_data in optimized_output:
        order_id = plan_order_data["order__id"]
        if order_id in optimized_order_dict:
            combined_entry = {**plan_order_data, **optimized_order_dict[order_id]}
            combined_entry['order_id'] = combined_entry.pop('order__id')
            combined_entry['order_number'] = combined_entry.pop('order__order_number')
            combined_results.append(combined_entry)

    df = pd.DataFrame(combined_results)
    df = timezone_formatter(df)
    df = df.fillna(0)
    return df


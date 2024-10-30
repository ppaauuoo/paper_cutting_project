from icecream import ic
from typing import Any, Dict, List
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime

from order_optimization.container import ModelContainer
from order_optimization.models import OptimizationPlan, OrderList, PlanOrder


def output_formatter(orders: pd.Series, init_out: int = 0) -> pd.DataFrame:
    """
    For formatting output by renaming and add an out column.
    """
    return pd.DataFrame(
        {
            "order_number": [orders["order_number"]],
            "num_orders": [orders["quantity"]],
            "cut_width": [orders["width"]],
            "cut_len": [orders["length"]],
            "type": [orders["edge_type"]],
            "deadline": [orders["due_date"]],
            "out": [init_out],
        }
    )


def results_formatter(
    optimizer_instance: ModelContainer,
    output_data: List[Dict[str, Any]],
    size_value: int,
    fitness_values: float,
    init_order_number: int,
    foll_order_number: int,
) -> Dict[str, Any]:
    """
    For formatting results obtain from optimizer to be one dict.
    """
    return {
        "output": output_data,
        "roll": optimizer_instance.PAPER_SIZE,
        "fitness": size_value + fitness_values,
        "trim": abs(fitness_values),
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number,
    }


def database_formatter(blade1_params, blade2_params_list) -> None:
    """
    For defining which order belong to which blade, and turn it into a model.

    return: Model
    """
    format_data = OptimizationPlan.objects.create()
    blade_2_orders = []
    update_list = []
    blade1_order = None

    blade1_order = PlanOrder.objects.create(**blade1_params)
    update_list.append(blade1_params['order'])

    for blade2_params in blade2_params_list:
        blade2_order = PlanOrder.objects.create(
            **blade2_params
        )
        blade_2_orders.append(blade2_order)
        update_list.append(blade2_params['order'])

    for order in update_list:
        ic(order.quantity)
        OrderList.objects.filter(id=order.id).update(quantity=order.quantity)

    format_data.blade_1.add(blade1_order)
    for order in blade_2_orders:
        format_data.blade_2.add(order)

    format_data.save()


def timezone_formatter(df: pd.DataFrame):
    """
    Format any timezone column in dataframe to be timezone unaware.
    """

    datetime_cols = df.select_dtypes(include=["datetime64[ns, UTC]"]).columns

    for col in datetime_cols:
        if is_datetime(df[col]):
            df[col] = df[col].dt.tz_localize(None)
        if is_datetime(df[col]):
            df[col] = df[col].dt.tz_localize(None)
    return df


def plan_orders_formatter() -> pd.DataFrame:
    """
    Request data from model and format it.
    """

    # Get all PlanOrder objects as a list of dictionaries
    optimized_output = list(
        PlanOrder.objects.all().values(
            "blade_1_orders__id",
            "blade_2_orders__id",
            "order_id",
            "plan_quantity",
            "out",
            "blade_type",
            "paper_roll",
            "order_leftover",
            "order_leftover",
        )
    )

    # Extract order IDs
    optimized_output_ids = [order["order_id"] for order in optimized_output]

    # Get corresponding OrderList objects
    optimized_order_list = list(
        OrderList.objects.filter(id__in=optimized_output_ids).values()
    )

    # Create a dictionary with order_id as the key
    optimized_order_dict = {order["id"]: order
                            for order in optimized_order_list}

    # Combine results
    for order in optimized_output:
        order_id = order["order_id"]
        if order_id in optimized_order_dict:
            order.update(optimized_order_dict[order_id])
    df = pd.DataFrame(optimized_output)
    df = timezone_formatter(df)
    df = df.fillna(0)

    return df

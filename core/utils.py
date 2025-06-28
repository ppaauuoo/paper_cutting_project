from typing import Any, Dict, List
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime


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
    optimizer_instance: Any,
    output_data: List[Dict[str, Any]],
    size_value: int,
    init_order_number: int,
    foll_order_number: int,
) -> Dict[str, Any]:
    """
    For formatting results obtain from optimizer to be one dict.
    """
    return {
        "output": output_data,
        "roll": optimizer_instance.PAPER_SIZE,
        "total": optimizer_instance.total,
        "trim": optimizer_instance.fitness_values,
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number,
    }


def timezone_formatter(df: pd.DataFrame):
    """
    Format any timezone column in dataframe to be timezone unaware.
    """
    datetime_cols = df.select_dtypes(include=["datetime64[ns, UTC]"]).columns

    for col in datetime_cols:
        if is_datetime(df[col]):
            df[col] = df[col].dt.tz_localize(None)
    return df

def get_production_quantity(output_data: List[Dict[str, Any]]) -> tuple[int, int]:
    """
    Calculate first order cut and second order cut.
    """
    init_len = output_data[0]["cut_len"]
    init_out = output_data[0]["out"]
    init_num_orders = output_data[0]["num_orders"]

    if len(output_data) <= 1:
        return (init_num_orders, init_num_orders)

    foll_order_len = output_data[1]["cut_len"]
    foll_out = output_data[1]["out"]

    try:
        foll_order_number = round(
            (init_len * init_num_orders * foll_out) / (foll_order_len * init_out)
        )
    except ZeroDivisionError:
        foll_order_number = 0
        print(f"Warning: ZeroDivisionError in get_production_quantity. Foll order length: {foll_order_len}, Init out: {init_out}")

    return (init_num_orders, foll_order_number)

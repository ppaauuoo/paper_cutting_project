from typing import Any, Dict, List
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from pandas.api.types import is_datetime64_any_dtype as is_datetime

from order_optimization.container import ModelContainer
from order_optimization.models import OptimizationPlan, OrderList, PlanOrder

from icecream import ic


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


def database_formatter(data: Dict[str, Any]) -> OptimizationPlan:
    """
    For defining which order belong to which blade, and turn it into a model.

    return: Model
    """
    format_data = OptimizationPlan.objects.create()
    blade_2_orders = []
    left_over_quantity = 0
    filtered_orders = []
    update_list=[]
    for item in data["output"]:
        current_id = item["id"]

        current_order = OrderList.objects.get(id=current_id)
        match item["blade"]:
            case 1:
                blade1_order = PlanOrder.objects.create(
                    order=OrderList.objects.get(id=current_id),
                    plan_quantity=data["init_order_number"],
                    out=item["out"],
                    paper_roll=data["roll"],
                    blade_type="Blade 1",
                    order_leftover=0,
                )
                current_order.quantity = 0
                update_list.append(current_order)

            case 2:
                #get combined out from second blade
                foll_out = sum(i['out'] for i in data["output"])-data["output"][0]['out']
                #calculate out ratio base from the combined out
                new_out_ratio = item['out']/foll_out
                #Calculate new cut for each common with foll cut from first blade divide by out ratio
                foll_cut = data["foll_order_number"]*new_out_ratio
                #add potential leftover from previous order
                plan_quantity = round(foll_cut + left_over_quantity)

                new_quantity = round(current_order.quantity  - foll_cut - left_over_quantity)
                #reset left over to zero
                left_over_quantity = 0

                #check if exceed the stock, then push it to leftover
                if new_quantity < 0:
                    left_over_quantity += abs(new_quantity)
                    new_quantity = 0
                    plan_quantity = current_order.quantity

                blade2_order = PlanOrder.objects.create(
                    order=OrderList.objects.get(id=current_id),
                    plan_quantity=plan_quantity,
                    out=item["out"],
                    paper_roll=data["roll"],
                    blade_type="Blade 2",
                    order_leftover=new_quantity
                )
                blade_2_orders.append(blade2_order)
                current_order.quantity = new_quantity
                update_list.append(current_order)


    if left_over_quantity:
        ic()
        raise ValueError("Both order are out of stock!")

    ic(update_list)
    for order in update_list:
        ic(order)
        OrderList.objects.filter(id=order.id).update(quantity=order.quantity)


    format_data.blade_1.add(blade1_order)
    for order in blade_2_orders:
        format_data.blade_2.add(order)

    format_data.save()


def timezone_formatter(df: pd.DataFrame):
    """
    Format any timezone column in dataframe to be timezone unaware.
    """


    datetime_cols = df.select_dtypes(include=['datetime64[ns, UTC]']).columns

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
    optimized_order_dict = {order["id"]: order for order in optimized_order_list}

    # Combine results
    for order in optimized_output:
        order_id = order["order_id"]
        if order_id in optimized_order_dict:
            order.update(optimized_order_dict[order_id])
    df = pd.DataFrame(optimized_output)
    df = timezone_formatter(df)
    df = df.fillna(0)

    return df

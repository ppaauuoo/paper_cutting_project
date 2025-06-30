from typing import Any, Dict, List, Optional
from pandas import DataFrame

from modules.new_ga import GA
from modules.hd import HD
from modules.lp import LP

from core.container import ModelContainer, OrderContainer, ProviderInterface, ModelInterface
from core.utils import get_production_quantity, results_formatter # For dependency injection / clarity

def get_optimizer(
    orders: DataFrame,
    size_value: Optional[float] = None,
    num_generations: int = 50,
    show_output: bool = False,
    blade: Optional[int] = None,
    common: bool = False,
    selector: Dict[str, Any] = None,
    progress_callback: Optional[Any] = None, # Added progress_callback
) -> ModelContainer:
    """
    Request and run the optimizer.
    """
    optimizer_instance = ModelContainer(
        model=GA(
            orders,
            size=size_value,
            num_generations=num_generations,
            showOutput=show_output,
            set_progress=progress_callback, # Pass the callback
            blade=blade,
            common=common,
            selector=selector
        ),
    )
    optimizer_instance.run()
    return optimizer_instance


def get_outputs(optimizer_instance: ModelContainer) -> List[Dict]:
    """
    Extract values from optimizer instance.
    """
    output_df = optimizer_instance.output.reset_index()
    output_data = output_df.to_dict("records")
    total = optimizer_instance.total
    if len(output_data) <= 0:
        raise ValueError("Solution Not Found")
    # if len(output_data) > 2 or total <= 0:
    #     raise ValueError("Solution Not Satisfied")

    return output_data


def get_common_optimizer_instance(
    orders: DataFrame,
    item: Dict[str, Any],
    results: Dict[str, Any],
    progress_callback: Optional[Any] = None,
) -> ModelContainer:
    """
    Configures and returns an optimizer instance for common order logic.
    """
    size_value = (item["cut_width"] * item["out"]) + results["trim"]
    optimizer_instance = get_optimizer(
        orders=orders,
        size_value=size_value,
        show_output=False,
        blade=2,
        common=True,
        selector=item,
        progress_callback=progress_callback,
    )
    return optimizer_instance


def set_common(
    results: Dict[str, Any],
    best_index: int,
    best_output: List[Dict],
    best_trim: float,
) -> Dict:
    """
    Remove the order chosen to be swapped by common orders, 
    then inject common orders and new fitness into results.
    """
    if results["output"]: # Ensure there's an element to pop
        results["output"].pop(best_index)  # remove the old order
    else:
        raise ValueError("Cannot set common: original output is empty.")

    results["init_order_number"] = results['output'][0]['num_orders'] if results['output'] else 0

    for item in results["output"]:
        item["blade"] = 1

    results["output"].extend(best_output)  # add the new one

    init_order = None
    foll_orders = []
    for item in results["output"]:
        if item.get("blade") == 1:
            init_order = item
        elif item.get("blade") == 2:
            foll_orders.append(item)
        else:
             if init_order is None and item["order_number"] == results['output'][0]["order_number"]:
                 init_order = item
             else:
                 foll_orders.append(item)


    init_len = init_order["cut_len"] if init_order else 0
    init_out = init_order["out"] if init_order["out"] else 0 

    results["init_order_number"] = init_order["num_orders"] if init_order else 0

    foll_len = 0
    foll_out = 0
    if foll_orders:
        foll_len = foll_orders[0]["cut_len"] # Assuming all foll_orders have same cut_len for this calculation
        foll_out = sum(item["out"] for item in foll_orders)


    new_total = sum(item["cut_width"] * item["out"] for item in results["output"])

    try:
        new_foll_number = round((
            init_len * results["init_order_number"] * foll_out) / (
                foll_len * init_out))
    except ZeroDivisionError:
        new_foll_number = 0
        print(f"Warning: ZeroDivisionError in set_common. foll_len: {foll_len}, init_out: {init_out}")
    except Exception as e:
        new_foll_number = 0
        print(f"Error calculating new_foll_number in set_common: {e}")

    results["total"] = new_total
    results["trim"] = best_trim
    results["foll_order_number"] = new_foll_number
    return results

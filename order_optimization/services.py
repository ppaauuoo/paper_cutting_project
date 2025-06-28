from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd # For handle_export, plan_orders_formatter

from order_optimization.adapters import OrderListAdapter, PlanOrderAdapter, OptimizationPlanAdapter
from order_optimization.formatter import (
    plan_orders_formatter,
    results_formatter,
)
from order_optimization.getter import (
    get_common,
    get_optimizer,
    get_orders,
    get_outputs,
    get_production_quantity,
)
from order_optimization.setter import set_common
from modules.lp import LP


class OptimizationService:
    def __init__(
        self,
        order_list_adapter: OrderListAdapter,
        plan_order_adapter: PlanOrderAdapter,
        optimization_plan_adapter: OptimizationPlanAdapter,
        file_id: str,
        max_trim: float,
        min_trim: float,
        roll_paper: List[int],
    ):
        self._order_list_adapter = order_list_adapter
        self._plan_order_adapter = plan_order_adapter
        self._optimization_plan_adapter = optimization_plan_adapter
        self._file_id = file_id
        self._max_trim = max_trim
        self._min_trim = min_trim
        self._roll_paper = roll_paper

    def _is_out_ok(self, output: List[Dict[str, Any]]) -> bool:
        acc_out = sum(item["out"] for item in output)
        return acc_out < 7

    def _is_foll_ok(self, output: List[Dict[str, Any]], foll_order_number: int) -> bool:
        """
        Check if second order's cut exceed the second order's stock or not.
        """
        foll_stock = 0
        if len(output) <= 1:
            return True
        for index, order in enumerate(output):
            if index == 0:
                continue
            foll_stock += order["num_orders"]
        if foll_stock < foll_order_number:
            return False
        return True

    def _is_trim_fit(self, trim: float) -> bool:
        """
        Check if trim exceed min/max tirm.
        """
        return trim <= self._max_trim and trim >= self._min_trim

    def _handle_results(self, orders: Any, size: Optional[float]) -> Dict[str, Any]:
        if orders is None:
            raise ValueError("Orders is empty!")

        optimizer_instance = get_optimizer(
            orders=orders,
            num_generations=50,
            show_output=False,
            size_value=size,
        )
        output_data = get_outputs(optimizer_instance)
        init_order_number, foll_order_number = get_production_quantity(output_data)

        results = results_formatter(
            optimizer_instance=optimizer_instance,
            output_data=output_data,
            size_value=size,
            init_order_number=init_order_number,
            foll_order_number=foll_order_number,
        )
        return results

    def _handle_switcher(self, results: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_trim_fit(results["trim"]):
            return results
        switcher = LP(results).run().get()
        if switcher is not None:
            results["trim"] = switcher["new_trim"]
            results["roll"] = switcher["new_roll"]
        return results

    def _handle_common(
        self, current_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Request orders base from the past results
        with common logic and run an optimizer.
        """
        if len(current_results["output"]) <= 1:
            return current_results
        best_trim = current_results["trim"]
        best_index: Optional[int] = None

        file_id = self._file_id

        for index, item in enumerate(current_results["output"]):
            optimizer_instance = get_common(
                file_id=file_id, item=item, results=current_results)
            if abs(optimizer_instance.fitness_values) <= best_trim:
                best_output = get_outputs(optimizer_instance)
                best_trim = optimizer_instance.fitness_values
                best_index = index
                break

        if best_index is not None:
            current_results = set_common(current_results, best_index, best_output, best_trim)

        return self._handle_switcher(current_results)

    def run_optimization_pipeline(self, start_date: str, stop_date: str, size: Optional[float]) -> Dict[str, Any]:
        """
        Runs the full optimization process, including initial configuration,
        results handling, switching, and common order handling.
        Returns the final optimization results or raises ValueError.
        """
        orders = get_orders(
            file_id=self._file_id, start_date=start_date, stop_date=stop_date
        )

        if orders is None:
            raise ValueError("Orders is empty!")

        results = self._handle_results(orders=orders, size=size)
        results = self._handle_switcher(results)
        results = self._handle_common(results=results)

        log = ""
        if self._is_trim_fit(results["trim"]):
            if self._is_foll_ok(results["output"], results["foll_order_number"]):
                if self._is_out_ok(results["output"]):
                    return results
                log = "out not ok"
            else:
                log = "stock not ok"
        else:
            log = f'trim not ok roll:{results["roll"]} trim:{ round(results["total"])}'

        raise ValueError(f"No Satisfiable Solution Found: {log}")


    def save_optimization_results(self, data: Dict[str, Any]) -> None:
        """
        Saves optimization results into the database using adapters.
        """
        if data is None:
            raise ValueError("Output is empty!")
        try:
            self._handle_database(data)
        except ValueError as e:
            raise ValueError(e)

    def reset_all_data(self) -> None:
        """
        Clears all orders and optimization plans from the database.
        """
        self._order_list_adapter.delete_all_orders()
        self._optimization_plan_adapter.delete_all_plans()

    def export_plan_orders(self) -> str:
        """
        Exports plan orders to an Excel file and returns the file path.
        """
        df = plan_orders_formatter()
        export_dir = "media/exports"
        # Ensure the directory exists
        import os
        os.makedirs(export_dir, exist_ok=True)
        file_path = f'{export_dir}/orders_export_{ datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx'
        df.to_excel(file_path, index=False)
        return file_path


    def _handle_database(self, data: Dict[str, Any]) -> None:
        if not data["output"]:
            raise ValueError("No output data to process")

        blade1_params = {}
        blade2_params_list = []
        left_over_quantity = 0

        order_adapter = self._order_list_adapter

        for item in data["output"]:
            current_id = item["id"]
            current_order = order_adapter.get_order(current_id)

            match item["blade"]:
                case 1:
                    blade1_params = {
                        "order": current_order,
                        "plan_quantity": data["init_order_number"],
                        "out": item["out"],
                        "paper_roll": data["roll"],
                        "blade_type": "Blade 1",
                        "order_leftover": 0,
                    }
                    order_adapter.update_order_quantity(current_id, 0)
                case 2:
                    foll_out = sum(i["out"] for i in data["output"][1:])
                    new_out_ratio = item["out"] / foll_out
                    foll_cut = data["foll_order_number"] * new_out_ratio
                    plan_quantity = round(foll_cut + left_over_quantity)
                    left_over_quantity = 0

                    new_quantity = round(current_order.quantity - plan_quantity)

                    if new_quantity < 0:
                        left_over_quantity += abs(new_quantity)
                        new_quantity = 0
                        plan_quantity = current_order.quantity

                    blade2_params = {
                        "order": current_order,
                        "plan_quantity": plan_quantity,
                        "out": foll_out,
                        "paper_roll": data["roll"],
                        "blade_type": "Blade 2",
                        "order_leftover": new_quantity,
                    }
                    order_adapter.update_order_quantity(current_id, new_quantity)
                    blade2_params_list.append(blade2_params)
                case _:
                    raise ValueError("Unsupported blade type")

        if left_over_quantity:
            raise ValueError("Order stock is out of limit!")

        if not blade1_params:
            raise ValueError("Blade 1 parameters could not be initialized.")

        plan_order_adapter = self._plan_order_adapter
        plan_order_adapter.create_plan_orders(blade1_params, blade2_params_list)

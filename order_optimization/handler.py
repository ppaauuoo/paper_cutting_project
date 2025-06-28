from typing import Any, Dict, Optional

from django.core.cache import cache

from order_optimization.adapters import (
    DjangoOrderListAdapter,
    DjangoPlanOrderAdapter,
    DjangoOptimizationPlanAdapter,
)
from order_optimization.data_loaders import get_processed_orders
from order_optimization.formatter import plan_orders_formatter
from order_optimization.setter import set_progress

from core.optimization_service import OptimizationService
from ordplan_project.settings import (
    CACHE_TIMEOUT,
    MAX_RETRY,
    MAX_TRIM,
    MIN_TRIM,
    ROLL_PAPER,
)

FILE_ID = "1"


def get_optimization_service() -> OptimizationService:
    """Helper to instantiate the optimization service with Django dependencies."""
    return OptimizationService(
        order_list_adapter=DjangoOrderListAdapter(),
        plan_order_adapter=DjangoPlanOrderAdapter(),
        optimization_plan_adapter=DjangoOptimizationPlanAdapter(),
        file_id=FILE_ID,
        max_trim=MAX_TRIM,
        min_trim=MIN_TRIM,
        roll_paper=ROLL_PAPER,
        progress_callback=set_progress,
        order_data_provider=get_processed_orders,
    )


def handle_auto_config(request: Any) -> Dict[str, Any]:
    """
    Handles automatic configuration requests in a Django context.
    Orchestrates the service calls and handles caching/error reporting.
    """
    service = get_optimization_service()

    start_date = request.POST.get("start_date")
    stop_date = request.POST.get("stop_date")
    size_str = request.POST.get("roll_pref", str(min(ROLL_PAPER)))
    size = float(size_str) if size_str else None

    again = cache.get("try_again", 0)

    try:
        results = service.run_optimization_pipeline(
            start_date=start_date,
            stop_date=stop_date,
            size=size
        )
        cache.delete("try_again")
        cache.set("optimization_results", results, CACHE_TIMEOUT)
        return results
    except ValueError as e:
        log_message = str(e)
        if "No Satisfiable Solution Found" in log_message:
            if again < MAX_RETRY:
                again += 1
                cache.set("try_again", again, CACHE_TIMEOUT)
                raise ValueError(f"No Satisfiable Solution Found. Retrying... (Attempt {again}/{MAX_RETRY})")
            else:
                best_result = cache.get("best_result")
                if best_result:
                    cache.set("optimization_results", best_result, CACHE_TIMEOUT)
                cache.delete("try_again")
                raise ValueError("No Satisfiable Solution Found after max retries.")
        
        cache.set("log", log_message, CACHE_TIMEOUT)
        cache.delete("try_again")
        raise e


def handle_saving(request: Any) -> None:
    """
    Pulls data from cache to save into the model.
    """
    service = get_optimization_service()

    cache.delete(f"order_cache_{FILE_ID}")
    data = cache.get("optimization_results", None)
    
    if data is None:
        raise ValueError("Output is empty! No optimization results to save.")
    
    try:
        service.save_optimization_results(data)
        cache.delete("optimization_results")
    except ValueError as e:
        raise ValueError(f"Error saving optimization results: {e}")


def handle_reset(request: Any) -> None:
    """
    Clears application cache and resets database data.
    """
    service = get_optimization_service()
    cache.clear()
    service.reset_all_data()


def handle_export(request: Any) -> str:
    """
    Exports data to an Excel file.
    """
    service = get_optimization_service()
    file_path = service.export_plan_orders(plan_orders_data_formatter_func=plan_orders_formatter)
    return file_path

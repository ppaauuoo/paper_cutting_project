from datetime import datetime
from typing import Any, Dict, Optional

from django.core.cache import cache

from order_optimization.adapters import (
    DjangoOrderListAdapter,
    DjangoPlanOrderAdapter,
    DjangoOptimizationPlanAdapter,
)
from order_optimization.services import OptimizationService
from ordplan_project.settings import (
    CACHE_TIMEOUT,
    MAX_RETRY,
    MAX_TRIM,
    MIN_TRIM,
    ROLL_PAPER,
)

FILE_ID = "1" # This could ideally come from request or configuration


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
    )


def handle_auto_config(request) -> Dict[str, Any]:
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
                # For retry, a redirect or re-rendering the form might be needed in a real web app.
                # Or the client side should re-initiate the request.
                # The current logic attempts a "recursive" retry which isn't suitable for web handlers.
                # For this refactor, we'll mimic the original logic as best as possible,
                # but acknowledge it's an anti-pattern for web requests.
                # Original "handle_auto_retry" logic moved here.
                # It originally took the 'best_result' from cache, implying a previous successful run.
                # This logic is very tightly coupled to the 'try_again' cache key.
                # Let's simplify this. If no solution, we log and raise.
                # The retry mechanism should be external to this function.
                raise ValueError(f"No Satisfiable Solution Found. Retrying... (Attempt {again}/{MAX_RETRY})")
            else:
                # Max retries reached, retrieve best previous result if any.
                best_result = cache.get("best_result") # This key is not set anywhere in this file. Needs to be handled by a higher layer or set by the service.
                if best_result:
                    cache.set("optimization_results", best_result, CACHE_TIMEOUT)
                cache.delete("try_again")
                raise ValueError("No Satisfiable Solution Found after max retries.")
        
        cache.set("log", log_message, CACHE_TIMEOUT)
        cache.delete("try_again")
        raise e


def handle_saving(request) -> None:
    """
    Pulls data from cache to save into the model.
    """
    service = get_optimization_service()

    file_id = FILE_ID # Still hardcoded, consider making this dynamic from request
    cache.delete(f"order_cache_{file_id}")
    data = cache.get("optimization_results", None)
    
    if data is None:
        raise ValueError("Output is empty! No optimization results to save.")
    
    try:
        service.save_optimization_results(data)
        cache.delete("optimization_results") # Clear results after saving
    except ValueError as e:
        raise ValueError(f"Error saving optimization results: {e}")


def handle_reset(request) -> None:
    """
    Clears application cache and resets database data.
    """
    service = get_optimization_service()
    cache.clear() # Clears Django's entire cache
    service.reset_all_data()


def handle_export(request) -> str:
    """
    Exports data to an Excel file.
    """
    service = get_optimization_service()
    file_path = service.export_plan_orders()
    return file_path

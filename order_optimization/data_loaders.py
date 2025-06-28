import pandas as pd
from django.core.cache import cache
from typing import Any, Dict, List, Optional
import pandas as pd

from ordplan_project.settings import CACHE_TIMEOUT
from order_optimization.models import OrderList
from order_optimization.setter import set_csv_file, set_model
from modules.hd import HD

from core.container import OrderContainer

def get_orders_cache(file_id: str) -> pd.DataFrame:
    """
    Get raw orders from cache or model, if there is nothing,
    populate model with file excel.
    """
    orders = cache.get(f"order_cache_{file_id}", None)

    if orders is not None and not orders.empty:
        return orders

    order_records = OrderList.objects.filter(file=set_csv_file(file_id))

    if order_records.exists():
        orders = pd.DataFrame(list(order_records.values()))
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
    else:
        set_model(file_id)

    order_records_after_set = OrderList.objects.filter(file=set_csv_file(file_id))
    if order_records_after_set.exists():
        orders = pd.DataFrame(list(order_records_after_set.values()))
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
        return orders
    
    return pd.DataFrame()


def get_processed_orders(
    file_id: str,
    common: bool = False,
    start_date: Optional[pd.Timestamp] = None,
    stop_date: Optional[pd.Timestamp] = None,
    common_init_order: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Pass args to order processor (HD provider).

    return: processed orders.
    """
    raw_orders = get_orders_cache(file_id)

    if raw_orders.empty:
        return pd.DataFrame()

    return OrderContainer(
        provider=HD(
            orders=raw_orders,
            common=common,
            start_date=start_date,
            stop_date=stop_date,
            common_init_order=common_init_order,
        )
    ).get()


def get_selected_order_from_request(request: Any) -> Dict[str, Any] | None:
    """
    Request order id and out from order selector (from a Django request).
    """
    selector_id = request.POST.get("selector_id")
    if not selector_id:
        return None
    selector_out = int(request.POST.get("selector_out"))
    return {"order_id": selector_id, "out": selector_out}

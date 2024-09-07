from pyparsing import str_type
from order_optimization.getter import get_orders
from order_optimization.handler import handle_auto_config


def optimizerController(request)->None:
    file_id = request.POST.get("file_id")
    start_date = request.POST.get("start_date")
    stop_date = request.POST.get("stop_date")
    orders = get_orders(request=request, file_id=file_id, start_date=start_date, stop_date=stop_date)
    
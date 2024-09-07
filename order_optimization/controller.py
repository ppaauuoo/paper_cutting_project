from pyparsing import str_type
from order_optimization.getter import get_orders
from order_optimization.handler import handle_auto_config, handle_saving


def optimizer_controller(request)->None:
    for i in range(0,5):
        handle_auto_config(request)
        handle_saving(request)

    
    
    
    
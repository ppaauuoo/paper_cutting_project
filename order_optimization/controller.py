from pyparsing import str_type
from order_optimization.getter import get_orders
from order_optimization.handler import handle_auto_config, handle_saving
from django.contrib import messages
from tqdm import tqdm
from icecream import ic
def optimizer_controller(request)->None:
    for i in tqdm(range(0,100)):
        try:
            handle_auto_config(request)
            handle_saving(request)
        except(ValueError) as e:
            ic(e)
            pass

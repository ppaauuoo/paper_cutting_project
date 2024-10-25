from order_optimization.handler import handle_auto_config, handle_saving
from tqdm import tqdm
from icecream import ic


def optimizer_controller(request) -> None:
    for i in tqdm(range(0, 50)):
        try:
            handle_auto_config(request)
            handle_saving(request)
        except ValueError as e:
            ic(e)
            pass

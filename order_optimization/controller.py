from order_optimization.handler import handle_auto_config, handle_saving
from tqdm import tqdm
from icecream import ic
from django.core.cache import cache
from ordplan_project.settings import (
    CACHE_TIMEOUT,
    )


def optimizer_controller(request) -> None:
    LENGTH = 10
    cache.delete("api_progress")
    for i in tqdm(range(1, LENGTH+1)):
        cache.get("api_progress", 0)
        try:
            handle_auto_config(request)
            handle_saving(request)
        except ValueError as e:
            ic(e)
            pass
        current_progress = i/LENGTH*100
        cache.set("api_progress", current_progress, CACHE_TIMEOUT)

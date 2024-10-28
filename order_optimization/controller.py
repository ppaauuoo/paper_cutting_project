from order_optimization.handler import handle_auto_config, handle_saving
from tqdm import tqdm
from icecream import ic
from django.core.cache import cache
from ordplan_project.settings import (
    CACHE_TIMEOUT,
    )


def optimizer_controller(request) -> None:
    LENGTH = 50
    for i in tqdm(range(0, LENGTH)):
        progress = cache.get("api_progress", 0)
        try:
            handle_auto_config(request)
            handle_saving(request)
        except ValueError as e:
            ic(e)
            pass
        cache.set("api_progress", progress/LENGTH*100, CACHE_TIMEOUT)
    cache.delete("api_progress")

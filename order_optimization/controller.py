from order_optimization.handler import handle_auto_config, handle_saving
from tqdm import tqdm
from icecream import ic
from django.core.cache import cache
from ordplan_project.settings import (
    CACHE_TIMEOUT,
    )


def optimizer_controller(request) -> None:
    LENGTH = 100
    REPEAT_ERROR = round(LENGTH*10/100)
    cache.delete("api_progress")
    e_count = 0
    for i in tqdm(range(1, LENGTH+1)):
        cache.get("api_progress", 0)
        try:
            handle_auto_config(request)
            try:
                handle_saving(request)
                e_count = 0
            except ValueError:
                raise

        except ValueError as e:
            ic(e)
            e_count += 1
        except RecursionError as e:
            ic(e)
            e_count += 1

        if e_count > REPEAT_ERROR:
            raise Exception("Error Exceed.")
            break
        current_progress = i/LENGTH*100
        cache.set("api_progress", current_progress, CACHE_TIMEOUT)

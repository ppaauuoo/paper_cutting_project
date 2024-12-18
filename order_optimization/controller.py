from order_optimization.handler import handle_auto_config, handle_saving
from django.core.cache import cache
from ordplan_project.settings import (
    CACHE_TIMEOUT,
)

import numpy as np

from rich.progress import Progress, TimeElapsedColumn

columns = [*Progress.get_default_columns(), TimeElapsedColumn()]


def optimizer_controller(request) -> None:
    LENGTH = 100
    REPEAT_ERROR = round(LENGTH * 10 / 100)
    cache.delete("api_progress")
    e_count = 0
    success_rates = []

    with Progress(*columns) as progress:
        task1 = progress.add_task("[red]Optimizing...", total=LENGTH)
        while not progress.finished:
            current_progress = cache.get("api_progress", 0)
            try:
                handle_auto_config(request)
                try:
                    handle_saving(request)
                    success_rate = round(1 / (e_count + 1) * 100)
                    success_rates.append(success_rate)
                    progress.console.print("Success Rate:", success_rate)
                    progress.console.print(
                        "Totle Rate:", round(np.mean(success_rates)))
                    e_count = 0
                    progress.update(task1, advance=1)
                except ValueError:
                    raise

            except ValueError as e:
                result = cache.get("optimization_results", None)
                log = cache.get("log", None)
                if result:
                    progress.console.print(result)
                progress.console.print(e, log)
                cache.delete("log")
                cache.delete("optimization_results")
                e_count += 1
            except RecursionError as e:
                progress.console.print(e)
                e_count += 1

            # if e_count > REPEAT_ERROR:
            #     progress.console.print("[red]Error Exceed.")
            #     progress.stop
            #     break
            current_progress = progress.tasks[task1].completed / LENGTH
            cache.set("api_progress", current_progress, CACHE_TIMEOUT)

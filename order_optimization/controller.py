from order_optimization.handler import handle_auto_config, handle_saving
from django.core.cache import cache
from ordplan_project.settings import (
    CACHE_TIMEOUT,
)

import numpy as np
from typing import Any


def optimizer_controller(request: Any) -> None:
    """
    Orchestrates the optimization process for a web request,
    handling retries and updating progress in cache.
    Note: This synchronous loop is an anti-pattern for typical web requests.
    Consider background tasks for long-running operations.
    """
    LENGTH = 100
    REPEAT_ERROR = round(LENGTH * 10 / 100)
    cache.delete("api_progress")
    e_count = 0
    total_success_rates = []

    for i in range(LENGTH):
        current_progress_ratio = (i + 1) / LENGTH
        cache.set("api_progress", current_progress_ratio, CACHE_TIMEOUT)

        try:
            handle_auto_config(request)
            
            try:
                handle_saving(request)
                success_rate_for_this_block = round(1 / (e_count + 1) * 100)
                total_success_rates.append(success_rate_for_this_block)
                print(f"Success Rate (current block): {success_rate_for_this_block}%")
                print(f"Total Average Success Rate: {round(np.mean(total_success_rates))}%")
                e_count = 0
                
            except ValueError as e_save:
                print(f"Error saving results: {e_save}")
                e_count += 1

            # if e_count > REPEAT_ERROR:
            #     progress.console.print("[red]Error Exceed.")
            #     progress.stop
            #     break
            current_progress = progress.tasks[task1].completed / LENGTH
            cache.set("api_progress", current_progress, CACHE_TIMEOUT)

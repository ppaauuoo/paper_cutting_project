from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class OrderListAdapter(ABC):
    @abstractmethod
    def get_order(self, order_id: str) -> Any:
        pass

    @abstractmethod
    def update_order_quantity(self, order_id: str, new_quantity: int) -> None:
        pass

    @abstractmethod
    def delete_all_orders(self) -> None:
        pass

class PlanOrderAdapter(ABC):
    @abstractmethod
    def create_plan_orders(self, blade1_params: Dict[str, Any], blade2_params_list: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def create_plan_order_instance(self, **kwargs: Any) -> Any:
        pass

class OptimizationPlanAdapter(ABC):
    @abstractmethod
    def create_optimization_plan(self, blade1_orders: List[Any], blade2_orders: List[Any]) -> Any:
        pass

    @abstractmethod
    def delete_all_plans(self) -> None:
        pass

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from order_optimization.models import OptimizationPlan, OrderList, PlanOrder
from core.interfaces import OrderListAdapter, PlanOrderAdapter, OptimizationPlanAdapter


class DjangoOrderListAdapter(OrderListAdapter):
    def get_order(self, order_id: str) -> OrderList:
        return OrderList.objects.get(id=order_id)

    def update_order_quantity(self, order_id: str, new_quantity: int) -> None:
        OrderList.objects.filter(id=order_id).update(quantity=new_quantity)

    def delete_all_orders(self) -> None:
        OrderList.objects.all().delete()


class DjangoPlanOrderAdapter(PlanOrderAdapter):
    def create_plan_orders(self, blade1_params: Dict[str, Any], blade2_params_list: List[Dict[str, Any]]) -> None:
        PlanOrder.objects.create(**blade1_params)
        for params in blade2_params_list:
            PlanOrder.objects.create(**params)

    def create_plan_order_instance(self, **kwargs: Any) -> PlanOrder:
        """Creates and returns a single PlanOrder instance."""
        return PlanOrder.objects.create(**kwargs)


class DjangoOptimizationPlanAdapter(OptimizationPlanAdapter):
    def create_optimization_plan(self, blade1_orders: List[PlanOrder], blade2_orders: List[PlanOrder]) -> OptimizationPlan:
        plan = OptimizationPlan.objects.create()
        plan.blade_1.add(*blade1_orders)
        plan.blade_2.add(*blade2_orders)
        return plan

    def delete_all_plans(self) -> None:
        OptimizationPlan.objects.all().delete()

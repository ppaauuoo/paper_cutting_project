from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# นำเข้า interfaces จาก core module
from core.interfaces import OrderListAdapter, PlanOrderAdapter, OptimizationPlanAdapter

# คลาสจำลองสำหรับข้อมูล OrderList และ PlanOrder ใน PyQt (คุณอาจจะต้องปรับให้ตรงกับ Model/Structure จริงใน PyQt)
class PyQtOrderListModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    
    def __repr__(self):
        return f"<PyQtOrderListModel id={self.id} quantity={self.quantity}>"

class PyQtPlanOrderModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return f"<PyQtPlanOrderModel order_id={self.order_id} plan_quantity={self.plan_quantity}>"

class PyQtOptimizationPlanModel:
    def __init__(self, blade1_orders: List[PyQtPlanOrderModel], blade2_orders: List[PyQtPlanOrderModel]):
        self.id = 1 # Mock ID
        self.blade_1_orders = blade1_orders
        self.blade_2_orders = blade2_orders
        self.created_at = "mock_datetime" # Mock datetime

    def __repr__(self):
        return f"<PyQtOptimizationPlanModel id={self.id}>"


class PyQtOrderListAdapter(OrderListAdapter):
    """
    Adapter สำหรับจัดการข้อมูล OrderList ในสภาพแวดล้อม PyQt
    (ปัจจุบันใช้ข้อมูลในหน่วยความจำ/List เป็นตัวอย่าง)
    """
    def __init__(self, initial_orders_data: List[Dict[str, Any]] = None):
        # ในการใช้งานจริง คุณอาจจะรับ Database connection หรือ File path ที่นี่
        self.orders: Dict[str, PyQtOrderListModel] = {}
        if initial_orders_data:
            for data in initial_orders_data:
                self.orders[data['id']] = PyQtOrderListModel(**data)

    def get_order(self, order_id: str) -> PyQtOrderListModel:
        # การดึงข้อมูล Order จากแหล่งข้อมูล PyQt
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError(f"Order with ID {order_id} not found.")
        return order

    def update_order_quantity(self, order_id: str, new_quantity: int) -> None:
        # การอัปเดต quantity ของ Order ในแหล่งข้อมูล PyQt
        if order_id in self.orders:
            self.orders[order_id].quantity = new_quantity
        else:
            print(f"Warning: Order with ID {order_id} not found for update.")

    def delete_all_orders(self) -> None:
        # การลบ Orders ทั้งหมดในแหล่งข้อมูล PyQt
        self.orders = {}
        print("All orders deleted from PyQt adapter memory.")


class PyQtPlanOrderAdapter(PlanOrderAdapter):
    """
    Adapter สำหรับจัดการข้อมูล PlanOrder ในสภาพแวดล้อม PyQt
    (ปัจจุบันใช้ข้อมูลในหน่วยความจำ/List เป็นตัวอย่าง)
    """
    def __init__(self, plan_orders_storage: List[PyQtPlanOrderModel] = None):
        # ในการใช้งานจริง คุณอาจจะรับ Database connection หรือ File path ที่นี่
        self.plan_orders = plan_orders_storage if plan_orders_storage is not None else []

    def create_plan_orders(self, blade1_params: Dict[str, Any], blade2_params_list: List[Dict[str, Any]]) -> None:
        # การสร้าง PlanOrder หลายรายการ (สำหรับ Django API)
        # ใน PyQt adapter นี้ เราจะใช้ create_plan_order_instance ทีละรายการ
        self.create_plan_order_instance(**blade1_params)
        for params in blade2_params_list:
            self.create_plan_order_instance(**params)
        print("Plan orders created in PyQt adapter memory.")

    def create_plan_order_instance(self, **kwargs: Any) -> PyQtPlanOrderModel:
        # การสร้างและคืนค่า PlanOrder Instance สำหรับ PyQt
        # `order` ใน kwargs จะเป็น PyQtOrderListModel
        plan_order = PyQtPlanOrderModel(
            order_id=kwargs.get('order').id if kwargs.get('order') else None,
            plan_quantity=kwargs.get('plan_quantity'),
            order_leftover=kwargs.get('order_leftover'),
            out=kwargs.get('out'),
            paper_roll=kwargs.get('paper_roll'),
            blade_type=kwargs.get('blade_type')
        )
        self.plan_orders.append(plan_order)
        return plan_order


class PyQtOptimizationPlanAdapter(OptimizationPlanAdapter):
    """
    Adapter สำหรับจัดการข้อมูล OptimizationPlan ในสภาพแวดล้อม PyQt
    (ปัจจุบันใช้ข้อมูลในหน่วยความจำ/List เป็นตัวอย่าง)
    """
    def __init__(self, optimization_plans_storage: List[PyQtOptimizationPlanModel] = None):
        # ในการใช้งานจริง คุณอาจจะรับ Database connection หรือ File path ที่นี่
        self.optimization_plans = optimization_plans_storage if optimization_plans_storage is not None else []

    def create_optimization_plan(self, blade1_orders: List[PyQtPlanOrderModel], blade2_orders: List[PyQtPlanOrderModel]) -> PyQtOptimizationPlanModel:
        # การสร้าง OptimizationPlan ในแหล่งข้อมูล PyQt
        plan = PyQtOptimizationPlanModel(blade1_orders, blade2_orders)
        self.optimization_plans.append(plan)
        print(f"Optimization plan {plan.id} created in PyQt adapter memory.")
        return plan

    def delete_all_plans(self) -> None:
        # การลบ OptimizationPlans ทั้งหมดในแหล่งข้อมูล PyQt
        self.optimization_plans = []
        print("All optimization plans deleted from PyQt adapter memory.")

import uuid
from django.db import models

class CSVFile(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='data/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class OrderList(models.Model):
    id = models.CharField(max_length=255, primary_key=True, editable=False, default=uuid.uuid4)  # Use UUID as default
    file = models.ForeignKey(CSVFile, on_delete=models.CASCADE)
    order_number = models.IntegerField(default=None)
    due_date = models.DateTimeField(default=None)
    front_sheet = models.CharField(max_length=5,default="not defined")
    c_wave = models.CharField(max_length=5,default="not defined")
    middle_sheet = models.CharField(max_length=5,default="not defined")
    b_wave = models.CharField(max_length=5,default="not defined")
    back_sheet = models.CharField(max_length=5,default="not defined")
    level = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
    length = models.IntegerField(default=0)
    left_edge_cut = models.IntegerField(default=0)
    middle_edge_cut = models.IntegerField(default=0)
    right_edge_cut = models.IntegerField(default=0)
    component_type = models.CharField(max_length=5,default="not defined")
    quantity = models.IntegerField(default=0)
    production_quantity = models.IntegerField(default=0)
    edge_type = models.CharField(max_length=5,default="not defined")
    order_status = models.CharField(max_length=5,default="not defined")
    excess_percentage = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_number}"


class PlanOrder(models.Model):
    order = models.ForeignKey(OrderList, on_delete=models.CASCADE)
    plan_quantity = models.IntegerField(default=0)
    order_leftover = models.IntegerField(default=0)
    out = models.IntegerField(default=0)
    paper_roll = models.IntegerField(default=0)
    blade_type = models.CharField(max_length=10, choices=[('blade_1', 'Blade 1'), ('blade_2', 'Blade 2')], default='blade_1')  # New field to specify blade type


class OptimizationPlan(models.Model):
    blade_1 = models.ManyToManyField(PlanOrder, related_name='blade_1_orders')
    blade_2 = models.ManyToManyField(PlanOrder, related_name='blade_2_orders', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"OptimizationPlan {self.id} created at {self.created_at}"
    



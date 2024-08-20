from django.db import models

class CSVFile(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='data/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class OptimizedOrder(models.Model):
    output = models.JSONField()  # Assuming the output is JSON data
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OptimizedOrder {self.id} created at {self.created_at}"

class OrderList(models.Model):
    file = models.ForeignKey(CSVFile, on_delete=models.CASCADE)
    due_date = models.DateTimeField(default="not defined")
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
    order_number = models.IntegerField(default=0)
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
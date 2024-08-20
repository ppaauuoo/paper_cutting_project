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
    กำหนดส่ง = models.DateTimeField(default="not defined")
    แผ่นหน้า = models.CharField(max_length=5,default="not defined")
    ลอน_C = models.CharField(max_length=5,default="not defined")
    แผ่นกลาง = models.CharField(max_length=5,default="not defined")
    ลอน_B = models.CharField(max_length=5,default="not defined")
    แผ่นหลัง = models.CharField(max_length=5,default="not defined")
    จน_ชั้น = models.IntegerField(default=0)
    กว้างผลิต = models.IntegerField(default=0)
    ยาวผลิต = models.IntegerField(default=0)
    ทับเส้นซ้าย = models.IntegerField(default=0)
    ทับเส้นกลาง = models.IntegerField(default=0)
    ทับเส้นขวา = models.IntegerField(default=0)
    เลขที่ใบสั่งขาย = models.IntegerField(default=0)
    ชนิดส่วนประกอบ = models.CharField(max_length=5,default="not defined")
    จำนวนสั่งขาย = models.IntegerField(default=0)
    จำนวนสั่งผลิต = models.IntegerField(default=0)
    ประเภททับเส้น = models.CharField(max_length=5,default="not defined")
    สถานะใบสั่ง = models.CharField(max_length=5,default="not defined")
    เปอร์เซ็นต์ที่เกิน = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.เลขที่ใบสั่งขาย}"
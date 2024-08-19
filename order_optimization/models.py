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
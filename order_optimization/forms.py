from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CSVFile

class CSVFileForm(forms.ModelForm):
    class Meta:
        model = CSVFile
        fields = ['name', 'file']

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
from django import forms
from django.contrib.auth.models import User
from .models import DoctorProfile, PatientProfile
from django.contrib.auth.forms import UserCreationForm

class UserSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

class DoctorSignupForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ['license_number', 'phone_number']

class PatientSignupForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ['phone_number', 'dob']

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Enter your name',
        'id': 'name',
        'required': True
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Enter your email',
        'id': 'email',
        'required': True
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Enter your message',
        'id': 'message',
        'rows': 5,
        'required': True
    }))
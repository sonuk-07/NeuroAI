from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta, date

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"Dr. {self.user.username}"

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, null=True, blank=True, on_delete=models.SET_NULL)
    phone_number = models.CharField(max_length=15)
    dob = models.DateField(default=date.today)

    def __str__(self):
        return f"{self.user.username}"

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp_code = ''.join(random.choices(string.digits, k=6))
        self.save()

    def is_valid(self):
        return timezone.now() - self.created_at <= timedelta(minutes=10)
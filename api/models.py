from django.db import models
from django.contrib.auth.models import User
from accounts.models import DoctorProfile

class ImageUpload(models.Model):
    STATUS_CHOICES = [
        ('none', 'None'),
        ('requested', 'Requested'),
        ('reviewed', 'Reviewed'),
    ]
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    disease_predict = models.CharField(max_length=100, blank=True, null=True)
    doctor_comment = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    request_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='none')

    def __str__(self):
        return f"{self.user.username} - {self.disease_predict}"


class RecommendationRequest(models.Model):
    image = models.ForeignKey(ImageUpload, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, related_name='recommendation_requests', on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, related_name='recommendation_requests', on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    disease_predict = models.CharField(max_length=100, blank=True, null=True)
    is_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation Request from {self.patient.username} to Dr. {self.doctor.user.username}"
    
    def mark_as_reviewed(self):
        """Mark this recommendation request as reviewed"""
        self.is_reviewed = True
        self.save()
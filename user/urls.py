# user/urls.py or doctor/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('settings/', views.settings, name='settings'),
    path('doctor/settings/', views.doctor_settings, name='doctor_settings'),
    path('update_password/', views.update_password, name='update_password'),
    path('update_email/', views.update_email, name='update_email'),
    path('update_username/', views.update_username, name='update_username'), 
    path('update_name/', views.update_name, name='update_name'),

]

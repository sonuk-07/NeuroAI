
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import *
from api.models import RecommendationRequest
from django.shortcuts import render, get_object_or_404, redirect
import random
from api.models import ImageUpload
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@login_required
def edit_profile(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        
        # Update the user's profile
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        return redirect('profile')

    return render(request, 'common/settings.html')

def settings(request):
    return render(request, 'common/settings.html')

@login_required
def update_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('new_username')
        confirm_username = request.POST.get('confirm_username')
        
        user = request.user

        if new_username and new_username == confirm_username:
            old_username = user.username
            user.username = new_username
            user.save()
            send_mail(
                'Username Changed',
                f'Your username has been changed from {old_username} to {new_username}.',
                'nayanai.innovate@gmail.com',
                [user.email],
                fail_silently=False,
            )
            messages.success(request, 'Username updated successfully.')
        else:
            messages.error(request, "Usernames do not match")
    
    return render(request, 'common/settings.html')

@login_required
def update_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect")
        elif new_password and new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            send_mail(
                'Password Changed',
                'Your password has been changed successfully.',
                'nayanai.innovate@gmail.com',
                [user.email],
                fail_silently=False,
            )
            messages.success(request, "Password updated successfully")
        elif new_password and new_password != confirm_password:
            messages.error(request, "New passwords do not match")
        
        return render(request, 'common/settings.html')
    
    return render(request, 'common/settings.html')


@login_required
def update_name(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        messages.success(request, 'Name updated successfully.')

    return render(request, 'common/settings.html')



@login_required
def update_email(request):
    if request.method == 'POST':
        current_email = request.POST.get('current_email')
        new_email = request.POST.get('new_email')
        confirm_email = request.POST.get('confirm_email')
        
        user = request.user

        if current_email != user.email:
            messages.error(request, "Current email is incorrect")
        elif new_email and new_email == confirm_email:
            user.email = new_email
            user.save()
            send_mail(
                'Email Changed',
                'Your email has been changed successfully.',
                'nayanai.innovate@gmail.com',
                [new_email],
                fail_silently=False,
            )
            messages.success(request, "Email updated successfully")
        elif new_email and new_email != confirm_email:
            messages.error(request, "New emails do not match")
        
        return render(request, 'common/settings.html')
    
    return render(request, 'common/settings.html')
@login_required
def doctor_dashboard(request):
    doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
    notifications = RecommendationRequest.objects.filter(doctor=doctor_profile, is_reviewed=False)

    context = {
        'doctor': doctor_profile,
        'notifications': notifications,
    }

    return render(request, 'doctor/dashboard.html', context)



def prediction(request):
    return render(request, 'patient/prediction.html')

def history(request):
    return render(request, 'patient/history.html')

def patient_settings(request):
    return render(request, 'common/settings.html')

def book_appointment(request):
    return render(request, 'patient/appointment.html')
def see_appointments(request):
    return render(request, 'doctor/appointments.html')

@login_required
def doctor_settings(request):
    try:
        doctor_profile = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        doctor_profile = None
    
    context = {
        'doctor_profile': doctor_profile
    }
    return render(request, 'doctor/doctor_settings.html', context)

    

    
    




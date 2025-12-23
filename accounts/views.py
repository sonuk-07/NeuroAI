
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import DoctorProfile, PatientProfile, OTP
from .forms import DoctorSignupForm, PatientSignupForm, ContactForm
import random
import string
from django.conf import settings
from django.utils import timezone


def profile_view(request):
    patientprofile = PatientProfile.objects.get(user=request.user)
    today = timezone.now().date()
    age = today.year - patientprofile.dob.year - ((today.month, today.day) < (patientprofile.dob.month, patientprofile.dob.day))

    return render(request, 'patient/profile.html', {
        'user': request.user,
        'patientprofile': patientprofile,
        'age': age,
    })

def signup(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        role = request.POST.get('role')

        # Password validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('signup')

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, f"Password error: {' '.join(e.messages)}")
            return redirect('signup')

        # Check for duplicate username or email
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('signup')
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken")
            return redirect('signup')

        # Create user
        user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name, last_name=last_name)
        user.save()

        # Process based on user role
        if role == 'doctor':
            license_number = request.POST.get('license_number')
            phone_number = request.POST.get('phone_number')
            doctor_profile = DoctorProfile(user=user, license_number=license_number, phone_number=phone_number)
            doctor_profile.save()
        elif role == 'patient':
            dob = request.POST.get('dob')
            phone_number = request.POST.get('phone_number')
            patient_profile = PatientProfile(user=user, dob=dob, phone_number=phone_number)
            patient_profile.save()

        # Send a confirmation email
        send_mail(
            'Welcome to Our Site!',
            'Thank you for signing up. We are excited to have you on board!',
            'from@example.com',  # Replace with your sender email
            [email],  # Send to the user's email
            fail_silently=False,
        )

        messages.success(request, "User created successfully. Please log in.")
        return redirect('login')  # Redirect to the login page after successful signup

    return render(request, 'auth/signup.html')


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # If user is authenticated, log them in
            login(request, user)

            # Check if the user is a doctor or patient and redirect accordingly
            if hasattr(user, 'doctorprofile'):
                return redirect('doctor_dashboard')  # Replace with your actual doctor dashboard URL name
            elif hasattr(user, 'patientprofile'):
                return redirect('upload_image')  # Replace with your actual patient dashboard URL name
            else:
                return redirect('home')  # Fallback to home page if no role is found
        else:
            # If authentication fails
            messages.error(request, "Invalid username or password")
            return redirect('login')

    return render(request, 'auth/login.html')


def forgot_password(request):
    if request.method == 'POST':
        email_or_username = request.POST.get('email_or_username')
        user = None
        
        # Check if it's an email or a username
        if '@' in email_or_username:
            # It's an email
            user = User.objects.filter(email=email_or_username).first()
        else:
            # It's a username
            user = User.objects.filter(username=email_or_username).first()

        if not user:
            messages.error(request, "No account found with that email or username.")
            return redirect('forgot_password')

        # Store email in session
        request.session['email'] = user.email

        # Generate OTP and send to user
        otp_instance = OTP(user=user)
        otp_instance.generate_otp()

        # Send OTP via email
        send_mail(
            'Password Reset OTP',
            f'Your OTP is: {otp_instance.otp_code}',
            'from@example.com',  # Replace with your sender email
            [user.email],
            fail_silently=False,
        )

        messages.success(request, "An OTP has been sent to your registered email.")
        return redirect('verify_otp')

    return render(request, 'auth/forgot_password.html')
def verify_otp(request):
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')  # Use .get() to avoid MultiValueDictKeyError

        if not otp_code:
            messages.error(request, "Please provide the OTP code.")
            return redirect('verify_otp')

        # Check if OTP code and email are provided
        user_email = request.session.get('email')
        if not user_email:
            messages.error(request, "No email address found. Please request OTP again.")
            return redirect('forgot_password')

        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            messages.error(request, "No user found with this email address.")
            return redirect('verify_otp')

        try:
            otp_instance = OTP.objects.get(user=user, otp_code=otp_code)
        except OTP.DoesNotExist:
            messages.error(request, "Invalid OTP code.")
            return redirect('verify_otp')

        if otp_instance.is_valid():
            # OTP is valid, proceed to password reset or further steps
            messages.success(request, "OTP verified successfully. You can now reset your password.")
            return redirect('reset_password')  # Replace with your actual password reset URL
        else:
            messages.error(request, "OTP has expired.")
            return redirect('verify_otp')

    return render(request, 'auth/verify_otp.html')


def reset_password(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('reset_password')

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, f"Password error: {' '.join(e.messages)}")
            return redirect('reset_password')

        email = request.session.get('email')  # Retrieve email from session
        if not email:
            messages.error(request, "No email address found. Please request OTP again.")
            return redirect('forgot_password')

        # Update user password
        user = User.objects.filter(email=email).first()
        if not user:
            messages.error(request, "User not found.")
            return redirect('forgot_password')

        user.set_password(password)
        user.save()

        # Clear the email from session after password reset
        request.session.pop('email', None)

        messages.success(request, "Password reset successfully. Please log in.")
        return redirect('login')

    return render(request, 'auth/reset_password.html')



def logout(request):
    auth_logout(request)
    return redirect('login')

def home(request):
    return render(request, 'core/index.html')

def about(request):
    return render(request, 'core/about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Get form data
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # Send email
            subject = f"Contact Form Submission from {name}"
            email_message = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
            recipient_email = "nayanai.innovate@gmail.com"  # Your email
            
            try:
                send_mail(subject, email_message, settings.DEFAULT_FROM_EMAIL, [recipient_email])
                messages.success(request, "Your message has been sent successfully!")
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
            
            return redirect('contact')  # Redirect to the contact page after submission
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})
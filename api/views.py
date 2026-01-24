from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ImageUploadForm
from .models import ImageUpload, RecommendationRequest
from accounts.models import DoctorProfile
from django.core.mail import send_mail
import os
from pathlib import Path

@login_required
def upload_image(request):
    detection_result = None
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image_upload = form.save(commit=False)
                image_upload.user = request.user
                image_upload.save()
                image_path = image_upload.image.path
                image_upload.disease_predict = predict_disease(image_path)
                image_upload.save()
                messages.success(request, 'Image uploaded and prediction completed.')
                detection_result = image_upload
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
    else:
        form = ImageUploadForm()
    return render(request, 'patient/dashboard.html', {'form': form, 'detection_result': detection_result})

@login_required
def history(request):
    uploaded_images = ImageUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'patient/history.html', {'uploaded_images': uploaded_images})

@login_required
def result(request, image_id):
    detection_result = get_object_or_404(ImageUpload, id=image_id, user=request.user)
    return render(request, 'patient/result.html', {'detection_result': detection_result})

@login_required
def request_recommendation(request, image_id):
    image = get_object_or_404(ImageUpload, id=image_id, user=request.user)
    if image.request_status == 'requested':
        messages.info(request, 'Recommendation request already sent.')
    else:
        try:
            doctor = DoctorProfile.objects.first()
            if doctor:
                RecommendationRequest.objects.create(
                    image=image, patient=request.user, doctor=doctor,
                    message="Please review this image.",
                    disease_predict=image.disease_predict
                )
                send_mail(
                    subject=f"Recommendation Request from {request.user.username}",
                    message=f"Patient: {request.user.username}\nPrediction: {image.disease_predict}",
                    from_email='noreply@neuroai.com',
                    recipient_list=[doctor.user.email],
                    fail_silently=True,
                )
                image.request_status = 'requested'
                image.save()
                messages.success(request, 'Request sent to doctor.')
            else:
                messages.error(request, 'No doctor available.')
        except DoctorProfile.DoesNotExist:
            messages.error(request, 'Unable to find doctor.')
    
    uploaded_images = ImageUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'patient/history.html', {'uploaded_images': uploaded_images})

@login_required
def respond_request(request, request_id):
    rec_request = get_object_or_404(RecommendationRequest, id=request_id, doctor__user=request.user)
    if request.method == 'POST':
        rec_request.image.doctor_comment = request.POST.get('doctor_comment')
        rec_request.image.request_status = 'reviewed'
        rec_request.image.save()
        rec_request.is_reviewed = True
        rec_request.save()
        messages.success(request, 'Recommendation sent.')
        doctor = request.user.doctorprofile
        recommendations = RecommendationRequest.objects.filter(doctor=doctor).order_by('-created_at')
        return render(request, 'doctor/doctor_recommendation_history.html', {'recommendations': recommendations})
    return render(request, 'doctor/respond_request.html', {'request': rec_request})

@login_required
def edit_recommendation(request, recommendation_id):
    rec = get_object_or_404(RecommendationRequest, id=recommendation_id, doctor__user=request.user)
    if request.method == 'POST':
        rec.image.doctor_comment = request.POST.get('comments', '')
        rec.image.save()
        rec.is_reviewed = True
        rec.save()
        messages.success(request, 'Recommendation updated.')
        doctor = request.user.doctorprofile
        recommendations = RecommendationRequest.objects.filter(doctor=doctor).order_by('-created_at')
        return render(request, 'doctor/doctor_recommendation_history.html', {'recommendations': recommendations})
    return render(request, 'doctor/edit_recommendation.html', {'recommendation': rec})

@login_required
def recommendation_history(request):
    doctor = request.user.doctorprofile
    recommendations = RecommendationRequest.objects.filter(doctor=doctor).order_by('-created_at')
    return render(request, 'doctor/doctor_recommendation_history.html', {'recommendations': recommendations})

@login_required
def delete_recommendation(request, recommendation_id):
    rec = get_object_or_404(RecommendationRequest, id=recommendation_id, doctor__user=request.user)
    if request.method == 'POST':
        rec.delete()
        messages.success(request, 'Recommendation deleted.')
    doctor = request.user.doctorprofile
    recommendations = RecommendationRequest.objects.filter(doctor=doctor).order_by('-created_at')
    return render(request, 'doctor/doctor_recommendation_history.html', {'recommendations': recommendations})

@login_required
def delete_image(request, image_id):
    image = get_object_or_404(ImageUpload, id=image_id, user=request.user)
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted.')
    uploaded_images = ImageUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'patient/history.html', {'uploaded_images': uploaded_images})


def predict_disease(image_path):
    """Predict brain tumor class from MRI image using DenseNet121."""
    try:
        import torch
        import cv2
        import albumentations as A
        from albumentations.pytorch import ToTensorV2
        
        CLASS_NAMES = ['glioma', 'meningioma', 'notumor', 'pituitary']
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        transform = A.Compose([
            A.Resize(224, 224),
            A.Normalize(mean=[0.4815, 0.4815, 0.4815], std=[0.2235, 0.2235, 0.2235]),
            ToTensorV2(),
        ])
        
        model_path = Path(__file__).parent.parent / 'models' / 'brain_resnet50.pt'
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        model = torch.jit.load(str(model_path), map_location=device)
        model.eval()
        
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        if len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        
        transformed = transform(image=img)
        tensor = transformed['image'].unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = model(tensor)
            prob = torch.softmax(output, dim=1)
            pred_class = torch.argmax(prob, dim=1).item()
            confidence = prob[0][pred_class].item() * 100
        
        return CLASS_NAMES[pred_class]
    except Exception as e:
        return f"Error: {str(e)}"

@login_required
def delete_all_images(request):
    if request.method == 'POST':
        ImageUpload.objects.all().delete()
        messages.success(request, 'All images deleted.')
    uploaded_images = ImageUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'patient/history.html', {'uploaded_images': uploaded_images})

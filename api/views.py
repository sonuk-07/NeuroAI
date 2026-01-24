from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ImageUploadForm
from .models import ImageUpload, RecommendationRequest
from accounts.models import DoctorProfile
from django.core.mail import send_mail  # For sending email recommendations

# Import only if needed
import os
from pathlib import Path

# Function to upload an image and predict the disease
@login_required
def upload_image(request):
    detection_result = None
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image_upload = form.save(commit=False)
                image_upload.user = request.user  # Link to the current user
                image_upload.save()  # Save first so image is stored on disk
                
                # Now predict using the saved image path
                image_path = image_upload.image.path
                image_upload.disease_predict = predict_disease(image_path)
                image_upload.save()  # Save prediction
                
                messages.success(request, 'Image uploaded and prediction saved successfully.')
                
                # Set the detection_result to show on the same page
                detection_result = image_upload

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                import traceback
                traceback.print_exc()  # Print full error for debugging
    else:
        form = ImageUploadForm()

    return render(request, 'patient/dashboard.html', {'form': form, 'detection_result': detection_result})


# Function to view the uploaded image history
@login_required
def history(request):
    uploaded_images = ImageUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'patient/history.html', {
        'uploaded_images': uploaded_images
    })


# Function to view the result of a specific image detection
@login_required
def result(request, image_id):
    detection_result = get_object_or_404(ImageUpload, id=image_id, user=request.user)
    return render(request, 'patient/result.html', {'detection_result': detection_result})


# Function for patients to request a recommendation from a doctor
@login_required
def request_recommendation(request, image_id):
    image = get_object_or_404(ImageUpload, id=image_id, user=request.user)

    if image.request_status == 'requested':
        messages.info(request, 'Recommendation request already sent.')
    else:
        try:
            doctor = DoctorProfile.objects.first()  # Assign a doctor (or handle multiple doctors)
            if doctor:
                # Create the recommendation request
                RecommendationRequest.objects.create(
                    image=image,
                    patient=request.user,
                    doctor=doctor,
                    message="Please review this image and provide your recommendation.",
                    disease_predict=image.disease_predict
                )

                # Optional: Email the doctor about the request
                send_mail(
                    subject=f"Recommendation Request from {request.user.username}",
                    message=f"Dear Dr. {doctor.user.username},\n\n"
                            f"Please review the following image and provide your recommendation.\n"
                            f"Prediction: {image.disease_predict}\n\n"
                            f"Best regards,\nYour System",
                    from_email='your_email@example.com',
                    recipient_list=[doctor.user.email],
                    fail_silently=False,
                )

                image.request_status = 'requested'
                image.save()
                messages.success(request, 'Request has been sent to the doctor with the prediction result.')
            else:
                messages.error(request, 'No doctor available at the moment.')
        except DoctorProfile.DoesNotExist:
            messages.error(request, 'Unable to find a doctor.')

    return redirect('history')


@login_required
def respond_request(request, request_id):
    recommendation_request = get_object_or_404(RecommendationRequest, id=request_id, doctor__user=request.user)

    if request.method == 'POST':
        comment = request.POST.get('doctor_comment')
        recommendation_request.image.doctor_comment = comment
        recommendation_request.image.request_status = 'reviewed'
        recommendation_request.image.save()  # Save updated comment in patient's history
        recommendation_request.is_reviewed = True
        recommendation_request.save()
        messages.success(request, 'Your recommendation has been sent to the patient.')
        return redirect('doctor_dashboard')

    return render(request, 'doctor/respond_request.html', {'request': recommendation_request})

@login_required
def edit_recommendation(request, recommendation_id):
    recommendation = get_object_or_404(RecommendationRequest, id=recommendation_id, doctor__user=request.user)

    if request.method == 'POST':
        comments = request.POST.get('comments', '')
        recommendation.image.doctor_comment = comments  # Update the doctor comment in the ImageUpload model
        recommendation.image.save()  # Save the changes to the image instance

        # Optional: Update is_reviewed status again
        recommendation.is_reviewed = True
        recommendation.save()

        messages.success(request, 'Recommendation updated successfully!')
        return redirect('recommendation_history')  # Redirect to history

    return render(request, 'doctor/edit_recommendation.html', {'recommendation': recommendation})

# View for doctors to see their recommendation history
@login_required
def recommendation_history(request):
    doctor = request.user.doctorprofile
    recommendations = RecommendationRequest.objects.filter(doctor=doctor).order_by('-created_at')  # Order by creation date or any relevant field
    return render(request, 'doctor/doctor_recommendation_history.html', {'recommendations': recommendations})


# Function for doctors to edit recommendation comments

@login_required
def delete_recommendation(request, recommendation_id):
    recommendation = get_object_or_404(RecommendationRequest, id=recommendation_id, doctor__user=request.user)

    if request.method == 'POST':
        recommendation.delete()
        messages.success(request, 'Recommendation deleted successfully!')
        return redirect('recommendation_history')

    return render(request, 'doctor/doctor_recommendation_history.html', {'recommendations': RecommendationRequest.objects.filter(doctor__user=request.user)})


# Function to delete an uploaded image
@login_required
def delete_image(request, image_id):
    image = get_object_or_404(ImageUpload, id=image_id, user=request.user)
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully.')
        return redirect('history')


def predict_disease(image_path):
    """
    Predict brain tumor class from MRI image using trained DenseNet121 model.
    Updated to match latest notebook with new dataset and preprocessing.
    Returns one of: 'glioma', 'meningioma', 'notumor', 'pituitary'
    """
    try:
        # Import ML dependencies (lazy import)
        import torch
        import cv2
        import numpy as np
        import albumentations as A
        from albumentations.pytorch import ToTensorV2
        
        # Define constants (MUST match notebook exactly)
        CLASS_NAMES = ['glioma', 'meningioma', 'notumor', 'pituitary']
        IMG_SIZE = 224
        
        # Get device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # ==================== DEFINE TRANSFORM (MUST MATCH NOTEBOOK) ====================
        # This is the exact transform from the notebook - validation/test pipeline
        val_test_transform = A.Compose([
            A.Resize(IMG_SIZE, IMG_SIZE),
            A.Normalize(mean=[0.4815, 0.4815, 0.4815], 
                       std=[0.2235, 0.2235, 0.2235]),
            ToTensorV2(),
        ])
        
        # Load model
        model_path = Path(__file__).parent.parent / 'models' / 'brain_resnet50.pt'
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        # Load TorchScript model (DenseNet121)
        model = torch.jit.load(str(model_path), map_location=device)
        model.eval()
        
        # ==================== READ AND PREPROCESS IMAGE ====================
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Convert to grayscale if RGB (training data is grayscale MRI)
        if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 3:
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
        
        # Apply histogram equalization (CLAHE) for better contrast on internet images
        img_gray_temp = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_gray_equalized = clahe.apply(img_gray_temp)
        img_bgr = cv2.cvtColor(img_gray_equalized, cv2.COLOR_GRAY2BGR)
        
        # ==================== APPLY TRANSFORM ====================
        # Apply the exact transform from notebook
        transformed = val_test_transform(image=img_bgr)
        img_tensor = transformed['image'].unsqueeze(0).to(device)
        
        # ==================== MAKE PREDICTION ====================
        with torch.no_grad():
            output = model(img_tensor)
            prob = torch.softmax(output, dim=1)
            pred_class = torch.argmax(prob, dim=1).item()
            confidence = prob[0][pred_class].item() * 100
        
        # Get predicted class name
        predicted_class = CLASS_NAMES[pred_class]
        
        # ==================== CONFIDENCE FILTERING ====================
        # If confidence is too low, warn that it might not be a valid brain MRI
        if confidence < 50:
            print(f"⚠️  WARNING: Low confidence prediction ({confidence:.1f}%)")
            print(f"   This might not be a valid brain MRI scan")
            return f"{predicted_class} (Low confidence - may not be valid MRI)"
        
        # ==================== DEBUG OUTPUT ====================
        print(f"✅ Prediction: {predicted_class} ({confidence:.1f}% confidence)")
        all_probs = [(CLASS_NAMES[i], prob[0][i].item()*100) for i in range(4)]
        print(f"   All probabilities: {all_probs}")
        
        return predicted_class
        
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return "Error in prediction"

from django.shortcuts import redirect
from .models import ImageUpload  # Adjust the import according to your model

def delete_all_images(request):
    if request.method == 'POST':
        ImageUpload.objects.all().delete()  # Delete all images
        # You can add a success message if you have messages set up
    return redirect('history')  # Redirect to the history page (update with the correct name)

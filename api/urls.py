from django.urls import path
from .views import upload_image, history, result, request_recommendation, delete_image, respond_request, recommendation_history, edit_recommendation, delete_recommendation, delete_all_images

urlpatterns = [
    path('upload/', upload_image, name='upload_image'),
    path('history/', history, name='history'),
    path('result/<int:image_id>/', result, name='result'),

    path('request-recommendation/<int:image_id>/', request_recommendation, name='request_recommendation'),
    path('respond-request/<int:request_id>/', respond_request, name='respond_request'),
    path('recommendation-history/', recommendation_history, name='recommendation_history'),
    path('edit-recommendation/<int:recommendation_id>/', edit_recommendation, name='edit_recommendation'),
path('recommendation/delete/<int:recommendation_id>/', delete_recommendation, name='delete_recommendation'),
    path('patient/history/delete_all/', delete_all_images, name='delete_all_images'),


    path('delete_image/<int:image_id>/', delete_image, name='delete_image'),
]
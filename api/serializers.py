from rest_framework import serializers
from .models import ImageUpload

class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageUpload
        fields = ['image', 'user']

class ImageRepredictSerializer(serializers.Serializer):
    id = serializers.IntegerField()

class SearchUserSerializer(serializers.Serializer):
    user = serializers.CharField(max_length=100)

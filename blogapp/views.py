from .serializers import *
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import *
from .forms import *
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from django.core.mail import send_mail
# from captcha.helpers import captcha_image_url
# from captcha.models import CaptchaStore
import requests
from .utils import get_client_ip
from django.conf import settings

secret_key = settings.RECAPTCHA_SECRET_KEY

class Submission(APIView):
  
  
  def post(self, request, *args, **kwargs):
    r = requests.post(
      'https://www.google.com/recaptcha/api/siteverify',
      data={
        'secret': secret_key,
        'response': request.data['g-recaptcha-response'],
        'remoteip': get_client_ip(self.request),  # Optional
      }
    )

    if r.json()['success']:
      # Successfuly validated
      # Handle the submission, with confidence!
      return self.create(request, *args, **kwargs)

    # Error while verifying the captcha 
    return Response(data={'error': 'ReCAPTCHA not verified.'}, status=status.HTTP_406_NOT_ACCEPTABLE)

# @api_view(["GET"])
# def get_captcha(request):
#     new_key = CaptchaStore.generate_key()
#     image_url = captcha_image_url(new_key)
#     return Response({"key": new_key, "image_url": image_url})


@api_view(['POST'])
def subscribe(request):
    serializer = SubscriberSerializer(data=request.data)
    if serializer.is_valid():
        subscriber = serializer.save()

        # Send confirmation email
        send_mail(
            subject="Subscription Successful - TechScribe",
            message="Thank you for subscribing! You'll receive blog updates soon.",
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[subscriber.email],
        )

        return Response({"message": "Subscribed successfully!"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BlogListPagination(PageNumberPagination):
    page_size = 3
    
@api_view(["GET"])
def blog_pagination(request):
    blogs = Blog.objects.all()
    paginator = BlogListPagination()
    paginated_blogs = paginator.paginate_queryset(blogs, request)
    serializer = BlogSerializer(paginated_blogs, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
def registerUser(request):

    # ✅ 1. Get token from frontend
    recaptcha_token = request.data.get("recaptcha_token")

    if not recaptcha_token:
        return Response(
            {"error": "Captcha token missing"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ✅ 2. Verify with Google
    google_verify_url = "https://www.google.com/recaptcha/api/siteverify"

    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": recaptcha_token,
    }

    r = requests.post(google_verify_url, data=payload)
    result = r.json()

    if not result.get("success"):
        return Response(
            {"error": "Invalid captcha"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ✅ 3. Create user
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# @api_view(['POST'])
# def registerUser(request):
    
#     form = RegistrationForm(request.data)
#     recaptcha_token = request.data.get("recaptcha_token")
#     if not form.is_valid():
#         return Response({"error": "Captcha incorrect or form invalid", "details": form.errors}, status=status.HTTP_400_BAD_REQUEST)
    
#     serializer = UserRegistrationSerializer(data=request.data)
#     if serializer.is_valid():
#         serializer.save()
#         return Response(serializer.data,status=status.HTTP_201_CREATED)
#     return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_blog(request):
    user = request.user
    serializer = BlogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=user)
        return Response(serializer.data)
    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def blog_list(request):
    blogs = Blog.objects.all()
    serializer = BlogSerializer(blogs, many=True)
    return Response(serializer.data)

# to get blogs with slug or id
@api_view(['GET'])
def blogs(request,slug):
    blog = Blog.objects.get(slug=slug)
    serializer = BlogSerializer(blog)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_blog(request,pk):
    user = request.user
    blog = Blog.objects.get(id=pk)
    if blog.author != user:
        return Response({'error':'Not authorized'},status=status.HTTP_403_FORBIDDEN)
    serializer = BlogSerializer(blog,data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_blog(request,pk):
    blog = Blog.objects.get(id=pk)
    if blog.author != request.user:
        return Response({'error':'Not authorized'},status=status.HTTP_403_FORBIDDEN)
    else:
        blog.delete()
        return Response({'success':'Blog deleted successfully'},status=status.HTTP_204_NO_CONTENT)
    
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    serializer = UpdateUserProfileSerializer(user,data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    username = user.username
    print(username)
    return Response({"username":username})

# @api_view(['GET'])
# def get_userinfo(request,username):
#     User = get_user_model()
#     user = User.objects.get(username=username)
#     serializer = UserInfoSerializer(user)
#     return Response(serializer.data)
@api_view(['GET'])
def get_userinfo(request, username):
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    serializer = UserInfoSerializer(user)
    return Response(serializer.data)


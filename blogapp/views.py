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
import requests
from .utils import get_client_ip
from django.conf import settings
# for oauth
from rest_framework.permissions import AllowAny
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        credential = request.data.get("credential")
        if not credential:
            print('❌ Missing credential')
            return Response({"error": "Missing credential"}, status=400)

        if settings.DEBUG:
            print('Google auth request data:', request.data)
            print('Using Google client ID:', settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY)

        if not settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            print('❌ Google Client ID not configured')
            return Response({
                "error": "Google authentication not configured",
                "detail": "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY is missing"
            }, status=500)

        try:
            id_info = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
                clock_skew_in_seconds=300,
            )
            if settings.DEBUG:
                print('✅ Google id_info verified:', id_info)
        except ValueError as exc:
            print('❌ Google token verification failed (invalid signature/format):', str(exc))
            return Response({
                "error": "Invalid Google token"
            }, status=400)
        except Exception as exc:
            print('❌ Google token verification failed:', str(exc))
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            return Response({
                "error": "Google authentication failed",
                "detail": str(exc) if settings.DEBUG else "Token verification error"
            }, status=400)

        email = id_info.get("email")
        if not email:
            print('❌ No email in Google response')
            return Response({
                "error": "Email not provided",
                "detail": "Google account must have email enabled"
            }, status=400)

        try:
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={"username": email.split("@")[0]}
            )
            print(f'✅ User {"created" if created else "retrieved"}:', user.username)
        except Exception as exc:
            print('❌ User creation failed:', str(exc))
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            return Response({
                "error": "User creation failed",
                "detail": str(exc) if settings.DEBUG else "Database error"
            }, status=500)

        try:
            refresh = RefreshToken.for_user(user)
            print('✅ JWT tokens generated successfully')
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "email": user.email,
                    "username": user.username,
                },
            })
        except Exception as exc:
            print('❌ Token generation failed:', str(exc))
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            return Response({
                "error": "Token generation failed",
                "detail": str(exc) if settings.DEBUG else "Authentication error"
            }, status=500)

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


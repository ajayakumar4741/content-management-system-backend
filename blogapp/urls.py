from django.urls import path
from .views import *

urlpatterns = [
    path('register/',registerUser,name='register'),
    path('create_blog/',create_blog,name='create_blog'),
    path('blog_list/',blog_list,name='blog_list'),
    path('update_blog/<int:pk>/',update_blog,name='update_blog'),
    path('delete_blog/<int:pk>/',delete_blog,name='delete_blog'),
    path('update_profile/',update_profile,name='update_profile'),
    path('get_username/',get_username,name='get_username'),
    path("blog_pagination", blog_pagination, name="blog_pagination"),
    path("blogs/<slug:slug>/", blogs, name="blogs"),
    path("get_userinfo/<str:username>/", get_userinfo, name="get_userinfo"),
    path("api/subscribe/", subscribe, name="subscribe"),
    # path("api/get_captcha/", get_captcha, name="get_captcha"),

]
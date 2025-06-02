
from django.contrib import admin
from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('signup/', views.SignUp, name='signup'),
    path('verify/<uidb64>/<token>/', views.verify_email, name='verify_email'),

    #password reset
    path('password_reset/', views.send_verification_code, name='send_verification_code'),
    path('password_reset/verify/', views.verify_code, name='verify_code'),
    path('password_reset/complete/', views.reset_password, name='reset_password'),


    #login
    path('login/', views.Login, name='login'),
    path('logout/', views.Logout, name='logout'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),


]
from urllib import request
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .forms import CustomUserCreationForm
import random
from django.contrib.auth import logout
from .utils import send_email_with_fallback  # Import your fallback function
from django.core.cache import cache
import time

User = get_user_model()

import random
import string
from Account.models import RoomTable

# for jwt
from .utils import generate_jwt
from django.http import JsonResponse

# jwt
from django.http import JsonResponse,HttpResponseRedirect
from .utils import decode_jwt

# login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
import json
import logging

logger = logging.getLogger('Account')  # must match logger name in settings


def generate_unique_room_id(username):
    base = username[:5].lower()  # first 5 chars for better uniqueness
    while True:
        rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        room_id = f"{base}{rand_part}"  # e.g., "vinayA1Z9"
        if not RoomTable.objects.filter(room_id=room_id).exists():
            return room_id


def SignUp(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                form.add_error('email', "Email is already in use.")
                return render(request, 'signup/Signup.html', {'form': form, 'debug': settings.DEBUG})
            
            # Create the user object but don't save yet
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Generate token and UID for verification link
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            verification_link = f"{settings.FRONTEND_VERIFY_URL}{uidb64}/{token}/"

            # Email content
            email_subject = 'Verify Your Email Address'
            email_body = render_to_string('account/verification_email.html', {
                'user': user,
                'verification_link': verification_link, 
            })

            try:
                # Use fallback email sending function
                success = send_email_with_fallback(
                    subject=email_subject,
                    message='Please click the verification link below.',
                    recipient_list=[user.email],
                    html_message=email_body,

                )

                if success:
                    # initializing the room table entry for user
                    RoomTable.objects.create(
                        username=user.username,
                        email=user.email,
                        room_id=generate_unique_room_id(user.username),  # You can use a function or UUID here
                    )
                    messages.success(request, f"User created! A verification email has been sent to {user.email}. Please verify your email to activate your account.")
                    # return redirect('account:login')
                    return render(request, 'signup/Signup.html',{'form': form,'debug': settings.DEBUG})
                
                else:
                    # Delete user if email sending failed
                    user.delete()
                    messages.error(request, "Failed to send verification email. Please try again later.")
                    return render(request, 'signup/Signup.html', {'form': form, 'debug': settings.DEBUG})
            except Exception as e:
                print(f"Email sending error: {e}")
                messages.error(request, "Failed to send verification email.")
                return render(request, 'signup/Signup.html', {'form': form, 'debug': settings.DEBUG})

        else:
            return render(request, 'signup/Signup.html', {'form': form, 'debug': settings.DEBUG})
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup/Signup.html', {'form': form, 'debug': settings.DEBUG})


def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)

        # If user already active, stop early
        if user.is_active:
            messages.info(request, "Your account is already verified.")
            return render(request, 'account/verify_email_page.html', {'debug': settings.DEBUG})

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Your account has been activated successfully!")
            return render(request, 'account/verify_email_page.html', {'debug': settings.DEBUG})

        else:
            messages.error(request, "Invalid or expired activation link.")
            return render(request, 'account/verify_email_page.html', {'debug': settings.DEBUG})

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, "Invalid activation link.")
        return render(request, 'account/verify_email_page.html', {'debug': settings.DEBUG})




def send_verification_code(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Check cooldown
            last_sent = cache.get(f'password_reset_{email}')
            if last_sent and time.time() - last_sent < 5 * 60:  # 5 minutes cooldown
                messages.error(request, 'Please wait 5 minutes before requesting another code.')
                return render(request, 'password_reset_request.html', {'debug': settings.DEBUG})

            try:
                user = User.objects.get(email=email)
                code = str(random.randint(1000, 9999))
                request.session['password_reset_email'] = email
                request.session['password_reset_code'] = code
                request.session.set_expiry(600)  # 10 minutes

                success = send_email_with_fallback(
                    subject='Your Verification Code',
                    message=f'Your verification code is: {code}',
                    recipient_list=[email]
                )

                if success:
                    cache.set(f'password_reset_{email}', time.time(), timeout=300)  # 5 min cooldown
                    messages.success(request, 'If this email exists, a verification code has been sent.')
                    return redirect('account:verify_code')

            except User.DoesNotExist:
                # Generic message for security
                messages.success(request, 'Email does not exist, check your mail id: Hint-check account  activation mail sent earlier')

    return render(request, 'password_reset_request.html', {'debug': settings.DEBUG})



def verify_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        session_code = request.session.get('password_reset_code')
        if code == session_code:
            return redirect('account:reset_password')
        else:
            messages.error(request, 'Invalid verification code.')
    return render(request, 'verify_code.html', {'debug': settings.DEBUG})


def reset_password(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        email = request.session.get('password_reset_email')
        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            # Cleanup session
            request.session.pop('password_reset_email', None)
            request.session.pop('password_reset_code', None)
            messages.success(request, 'Password reset successfully.')
            return redirect('account:login')
        except User.DoesNotExist:
            messages.error(request, 'Error resetting password.')
    return render(request, 'reset_password.html', {'debug': settings.DEBUG})



def Login(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)

        if not username or not password:
            return JsonResponse({"detail": "Username and password are required."}, status=400)

        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                # Send activation email again
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                verification_link = f"{settings.FRONTEND_VERIFY_URL}{uidb64}/{token}/"

                email_subject = 'Activate Your Account'
                email_body = render_to_string('account/verification_email.html', {
                    'user': user,
                    'verification_link': verification_link,
                })

                send_email_with_fallback(
                    subject=email_subject,
                    message='Please click the verification link below.',
                    recipient_list=[user.email],
                    html_message=email_body,
                )

                return JsonResponse({
                    "detail": f"Your account is inactive. We sent a verification email to {user.email}."
                }, status=403)

        except User.DoesNotExist:
            return JsonResponse({"detail": "Account does not exist."}, status=404)

        # Authenticate the user
        form = AuthenticationForm(request, data={'username': username, 'password': password})
        if form.is_valid():
            payload = {'username': user.username}
            token = generate_jwt(payload)
            logger.info("Received login request")

            # Create response and set token as cookie
            response = JsonResponse({'message': 'Login successful'})
            response.set_cookie(
                key='jwt',
                value=token,
                path='/',             # Accessible on all paths
                httponly=False,
                samesite=None, #'Lax',
                secure=False  # Set to True if using HTTPS
            )
            logger.info("Receivedone respnese")

            return response
        else:
            return JsonResponse({"detail": "Invalid username or password."}, status=401)

    return render(request, 'login/Login.html', {'form': AuthenticationForm(),'debug': settings.DEBUG})



def Logout(request):
    response = redirect('account:login')
    response.delete_cookie('jwt')   # Or 'access' — use the correct cookie name
    return response

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

User = get_user_model()


def SignUp(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                form.add_error('email', "Email is already in use.")
                return render(request, 'signup/Signup.html', {'form': form})

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
                    messages.success(request, "User created! A verification email has been sent.")
                    return redirect('login')
                else:
                    messages.error(request, "Failed to send verification email. Please try again later.")
                    return render(request, 'signup/Signup.html', {'form': form})
            except Exception as e:
                print(f"Email sending error: {e}")
                messages.error(request, "Failed to send verification email.")
                return render(request, 'signup/Signup.html', {'form': form})

        else:
            return render(request, 'signup/Signup.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup/Signup.html', {'form': form})


def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Your account has been activated successfully!")
            return redirect('login')
        else:
            messages.error(request, "Invalid or expired activation link.")
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, "Invalid activation link.")
    return redirect('signup')


def send_verification_code(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.get(email=email)
        if user !=None:
            try:
                user = User.objects.get(email=email)
                code = str(random.randint(1000, 9999))
                request.session['password_reset_email'] = email
                request.session['password_reset_code'] = code

                # Send the code using the fallback function
                success = send_email_with_fallback(
                    subject='Your Verification Code',
                    message=f'Your verification code is: {code}',
                    recipient_list=[email]
                )

                if success:
                    messages.success(request, 'Verification code sent to your email.')
                    return redirect('verify_code')
                else:
                    messages.error(request, 'Failed to send verification code. Please try again later.')
            except User.DoesNotExist:
                messages.error(request, 'No user with this email.')
    return render(request, 'password_reset_request.html')


def verify_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        session_code = request.session.get('password_reset_code')
        if code == session_code:
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid verification code.')
    return render(request, 'verify_code.html')


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
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Error resetting password.')
    return render(request, 'reset_password.html')


# login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login

def Login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')  # Username field often holds email if using email login

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

                messages.error(
                    request,
                    f"Your account is inactive. We've sent you a new verification email.{user.email} Please activate your account before logging in."
                )
                return redirect('login')

        except User.DoesNotExist:
            messages.error(request,f"Account Doesnot Exist")
            return redirect('login')

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password!")
    else:
        form = AuthenticationForm()
    
    return render(request, 'login/login.html', {'form': form})


def Logout(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('login')  # Redirect to your login page after logout
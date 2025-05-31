from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import get_connection
import jwt
from django.shortcuts import redirect
from datetime import datetime, timedelta

def send_email_with_fallback(subject, message, recipient_list, html_message=None):
    accounts = settings.EMAIL_ACCOUNTS

    # Try primary account
    try:
        connection = get_connection(
            host=accounts['primary']['HOST'],
            port=accounts['primary']['PORT'],
            username=accounts['primary']['USER'],
            password=accounts['primary']['PASSWORD'],
            use_tls=accounts['primary']['USE_TLS']
        )
        send_mail(
            subject,
            message,
            accounts['primary']['FROM'],
            recipient_list,
            connection=connection,
            fail_silently=False,
            html_message=html_message,  # ✅ added here
        )
        return True
    except Exception as e:
        print(f"Primary email failed: {e}")

    # Try secondary account
    try:
        connection = get_connection(
            host=accounts['secondary']['HOST'],
            port=accounts['secondary']['PORT'],
            username=accounts['secondary']['USER'],
            password=accounts['secondary']['PASSWORD'],
            use_tls=accounts['secondary']['USE_TLS']
        )
        send_mail(
            subject,
            message,
            accounts['secondary']['FROM'],
            recipient_list,
            connection=connection,
            fail_silently=False,
            html_message=html_message,  # ✅ added here
        )
        return True
    except Exception as e:
        print(f"Secondary email failed: {e}")

    return False


# jwt integration

def generate_jwt(payload):
    payload['exp'] = datetime.utcnow() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

def decode_jwt(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # Optional: re-issue token if expiry < 5 mins
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


from functools import wraps
from django.contrib.auth import get_user_model
User = get_user_model()

def jwt_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        token = request.COOKIES.get('jwt')
        if not token:
            return redirect('login')

        payload = decode_jwt(token)
        if not payload:
            return redirect('login')

        try:
            user = get_user_model().objects.get(username=payload.get('username'))
            request.user = user  # Attach full user instance
        except User.DoesNotExist:
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return _wrapped_view



# for jt=wt middle ware for websocket
import urllib.parse
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from jwt import decode as jwt_decode
from django.conf import settings
from channels.db import database_sync_to_async

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        cookies = headers.get(b"cookie", b"").decode()
        cookies = dict(cookie.strip().split("=", 1) for cookie in cookies.split(";") if "=" in cookie)
        
        token = cookies.get("access_token")
        if token:
            try:
                payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                scope["user"] = await get_user(payload["user_id"])
            except Exception:
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

@database_sync_to_async
def get_user(user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import get_connection
import jwt
from django.shortcuts import redirect
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)
logger.debug("WebSocket connected")

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
        logger.info(f"came to jwt required: {request}")
        token = request.COOKIES.get('jwt')
        if not token:
            return redirect('login')

        payload = decode_jwt(token)
        if not payload:
            return redirect('login')

        try:
            user = get_user_model().objects.get(username=payload.get('username'))
            request.user = user  # Attach full user instance
            logger.info("jwt verified")
        except User.DoesNotExist:
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return _wrapped_view



from django.conf import settings
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from jwt import decode, ExpiredSignatureError, InvalidTokenError
from urllib.parse import parse_qs
@database_sync_to_async
def get_user(validated_token):
    try:
        username = validated_token.get("username")
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        logger.debug("Came to middleware")

        # Extract token from query string
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        jwt_token_list = query_params.get("token", [])
        jwt_token = jwt_token_list[0] if jwt_token_list else None

        if jwt_token:
            try:
                validated_payload = decode_jwt(jwt_token)
                logger.debug("User detected")
                user = await get_user(validated_payload)
                logger.debug(f"User loaded: {user}")

                if user:
                    scope["user"] = user
                    return await super().__call__(scope, receive, send)
            except (ExpiredSignatureError, InvalidTokenError) as e:
                logger.warning(f"JWT error: {e}")

        # Reject unauthorized connections
        await send({
            "type": "websocket.close",
            "code": 4401,
        })
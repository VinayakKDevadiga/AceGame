from django.shortcuts import render,redirect
from Account.utils import jwt_required, decode_jwt
import logging
from AceGame import settings

logger = logging.getLogger("Sokkatte")  # must match logger name in settings
logger.debug("WebSocket connected")


# Create your views here.
@jwt_required
def StartGame(request):
    logger.info(f"logged in and request object is : {request}")
    token = request.COOKIES.get('jwt')
    if not token:
        return redirect('account:login')
    # get the Completed games from the view which is in 
    username = None
    logger.info(f"token in view of sokkatte : {token}")
    if token:
        payload = decode_jwt(token)
        if payload:
            username = payload.get('username')
            logger.info(f" Home  request{username}")
    response = render(request, 'Sokkatte_home_page.html', {'name': username, 'debug': settings.DEBUG})
    # if token:
        # response.set_cookie('jwt', token, path='/', samesite='Lax')
    return response


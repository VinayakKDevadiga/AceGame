from django.shortcuts import render
from Account.utils import jwt_required, decode_jwt
import logging
logger = logging.getLogger(__name__)
logger.debug("WebSocket connected")


# Create your views here.
@jwt_required
def StartGame(request):
    logger.info(f"logged in and request object is : {request}")
    token = request.COOKIES.get('jwt')
    username = None
    if token:
        payload = decode_jwt(token)
        if payload:
            username = payload.get('username')
            logger.info(f" Home  request{username}")
    return render(request, 'Sokkatte_home_page.html',{'username': username})

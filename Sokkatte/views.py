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
    logger.info(f"token in view of sokkatte : {token}")
    if token:
        payload = decode_jwt(token)
        if payload:
            username = payload.get('username')
            logger.info(f" Home  request{username}")
    response = render(request, 'Sokkatte_home_page.html', {'name': username})
    # if token:
        # response.set_cookie('jwt', token, path='/', samesite='Lax')
    return response

@jwt_required
def Game_Over(request):
    logger.info(f"logged in and request object is : {request}")
    token = request.COOKIES.get('jwt')
    username = None
    logger.info(f"token in view of sokkatte : {token}")
    if token:
        payload = decode_jwt(token)
        if payload:
            username = payload.get('username')
            logger.info(f" Home  request{username}")

    looser = request.GET.get('looser')
    completed_json = request.GET.get('completed')
    try:
        game_completed_player_list = json.loads(completed_json) if completed_json else []
    except Exception:
        game_completed_player_list = []
    response = render(request, 'winner_page.html', {
        'looser': looser,
        'game_completed_player_list': game_completed_player_list,
        'username': username,  # Use the JWT username variable here
    })
    # if token:
        # response.set_cookie('jwt', token, path='/', samesite='Lax')
    return response
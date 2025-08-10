from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from Account.models import RoomTable
from django.contrib import messages

# jwt
from Account.utils import jwt_required, decode_jwt
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Create your views here.
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()
import logging
logger = logging.getLogger('myapp')  # must match logger name in settings

def Home(request):

    token = request.COOKIES.get('jwt')
    username = None
    if token:
        payload = decode_jwt(token)
        if payload:
            username = payload.get('username')
            logger.info(f" Home  request{username}")

    return render(request, 'Homepage.html', {'username': username})


@csrf_exempt
def get_user(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return JsonResponse({'detail': 'Authorization header missing or invalid'}, status=401)

    token = auth_header.split(' ')[1]

    try:
        payload = decode_jwt(token)
        username = payload.get('username')
        logger.info(f"Received getuser request for: {username}")

        return JsonResponse({'username': username})

    except Exception as e:
        return JsonResponse({'detail': 'Invalid token', 'error': str(e)}, status=401)


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@jwt_required
def CreateRoom(request):
    token = request.COOKIES.get('jwt')
    username = None
    if token:
        payload = decode_jwt(token)
        if payload:
            username = payload.get('username')
            
    try:
        room = RoomTable.objects.get(username=username)
    except RoomTable.DoesNotExist:
        return JsonResponse({'detail': 'Room not found for this user.'}, status=404)

    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            new_password = data.get('password')
            if new_password:
                room.password = new_password
                room.save()
                return JsonResponse({'detail': 'Room password updated successfully!'}, status=200)
            else:
                return JsonResponse({'detail': 'Password required.'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    return render(request, 'Room/createroom.html', {
        'room_id': room.room_id,
        'password': room.password
    })


# Starts the websocket
@jwt_required
def Waitforplayers(request):
    return render(request,'Room/waitforplayers.html')

@jwt_required
def Join_room(request):
    if request.method == "POST":
        room_id = request.POST['room_id']
        password = request.POST['password']

        try:
            room = RoomTable.objects.get(room_id=room_id)
            if room.password == password:
                # Save user to room or mark as joined
                return redirect('waitforplayers')  # or wherever needed
            else:
                messages.error(request, "Incorrect password.")
        except RoomTable.DoesNotExist:
            messages.error(request, "Room does not exist.")
    
    return render(request, 'Room/joinroom.html')

@jwt_required
def Gamepage(request):
    return render(request, 'Room/gamepage.html')
    
@jwt_required
def Rulepage(request):
    return render(request, 'Room/rules.html')
    
@jwt_required
def Playgame(request):
    game_types = [
        {'id': 1, 'name': 'Poker'},
        {'id': 2, 'name': 'Blackjack'},
        {'id': 3, 'name': 'Solitaire'},
        {'id': 4, 'name': 'Bridge'}
    ]
    return render(request, 'playgame.html', {'game_types': game_types})

import json
from django_redis import get_redis_connection

def save_player_cards(room_id, player, cards):
    redis_conn = get_redis_connection("default")
    key = f'game_room:{room_id}'
    redis_conn.hset(key, player, json.dumps(cards))

def get_player_cards(room_id, player):
    redis_conn = get_redis_connection("default")
    key = f'game_room:{room_id}'
    data = redis_conn.hget(key, player)
    if data:
        return json.loads(data)
    return None

def get_all_players_in_room(room_id):
    redis_conn = get_redis_connection("default")
    key = f'game_room:{room_id}'
    all_data = redis_conn.hgetall(key)
    # Decode JSON and bytes
    return {player.decode(): json.loads(cards) for player, cards in all_data.items()}



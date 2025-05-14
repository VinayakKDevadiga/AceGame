from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from Account.models import RoomTable
from django.contrib import messages
# Create your views here.

def Home(request):
    return render(request, 'HomePage.html')


@login_required(login_url='login')
def CreateRoom(request):
    username = request.user.username

    try:
        room = RoomTable.objects.get(username=username)
    except RoomTable.DoesNotExist:
        messages.error(request, "Room not found for this user.")
        return redirect('playgame')  # Or handle as needed

    if request.method == 'POST':
        new_password = request.POST.get('password')
        if new_password:
            room.password = new_password
            room.save()
            messages.success(request, "Room password updated successfully!")
        return redirect('waitforplayers')  # Refresh after update

    return render(request, 'Room/createroom.html', {
        'room_id': room.room_id,
        'password': room.password
    })

# Starts the websocket
@login_required(login_url='login')
def Waitforplayers(request):
    return render(request,'Room/waitforplayers.html')

@login_required(login_url='login')
def join_room(request):
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



from django.shortcuts import render

@login_required(login_url='login')
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



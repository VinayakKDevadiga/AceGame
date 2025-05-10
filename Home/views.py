from django.shortcuts import render

# Create your views here.

def Home(request):
    return render(request, 'HomePage.html')


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

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

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


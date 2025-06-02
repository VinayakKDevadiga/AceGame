from django.shortcuts import render

# Create your views here.
def StartGame(request):
    return render(request, 'Sokkatte_home_page.html')
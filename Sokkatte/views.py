from django.shortcuts import render
from Account.utils import jwt_required, decode_jwt

# Create your views here.
@jwt_required
def StartGame(request):
    return render(request, 'Sokkatte_home_page.html')

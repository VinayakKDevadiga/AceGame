import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AceGame.settings')  # adjust if project name is different
django.setup()  

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from Account.utils import JWTAuthMiddleware
import AceGame.routing  # or wherever your websocket_urlpatterns live

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                AceGame.routing.websocket_urlpatterns
            )
        )
    ),
})

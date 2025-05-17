import os,django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AceGame.settings')  # adjust if project name is different
django.setup()  

import Home.routing  # Make sure this file exists and has `websocket_urlpatterns`

from channels.sessions import SessionMiddlewareStack

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            Home.routing.websocket_urlpatterns
        )
    ),
})

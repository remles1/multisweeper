from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/lobby/<lobby_id>", consumers.PlayerConsumer.as_asgi()),
]

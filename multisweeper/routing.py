from django.urls import path, re_path

from . import consumers

websocket_urlpatterns = [
    path("ws/lobby/<lobby_id>", consumers.PlayerConsumer.as_asgi()),
]

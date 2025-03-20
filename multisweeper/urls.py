from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("create-lobby/", views.create_lobby, name="create_lobby"),
    path("lobby/<str:lobby_id>/", views.lobby, name="lobby"),
    path("lobby-full/", views.lobby_full, name="lobby_full"),
    path("game-in-progress/", views.game_in_progress, name="game_in_progress"),
    path("pick-username/", views.pick_username, name="pick_username")
]

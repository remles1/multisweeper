from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("create-lobby/", views.create_lobby, name="create_lobby"),
    path("lobby/<str:lobby_id>/", views.lobby, name="lobby"),
]
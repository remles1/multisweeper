from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("lobby/<str:lobby_id>", views.lobby, name="lobby")
]
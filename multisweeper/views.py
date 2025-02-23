from django.shortcuts import render

from multisweeper.game.lobby import lobbies, Lobby


def index(request):
    return render(request, "multisweeper/index.html")


def lobby(request, lobby_id):
    if lobby_id not in lobbies:
        lobbies[lobby_id] = Lobby(2)
    return render(request, "multisweeper/lobby.html", {"lobby_id": lobby_id})

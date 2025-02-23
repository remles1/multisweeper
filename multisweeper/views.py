import uuid

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, redirect

from multisweeper.game.lobby import lobbies, Lobby


def index(request):
    return render(request, "multisweeper/index.html", {"lobbies": lobbies})


def create_lobby(request):
    if request.method == 'POST':
        lobby_id = str(uuid.uuid4())
        lobby = Lobby(lobby_id=lobby_id, max_players=2)
        lobbies[lobby_id] = lobby
        return redirect(f'/lobby/{lobby_id}')
    else:
        raise PermissionDenied()


def lobby(request, lobby_id):
    if lobby_id not in lobbies:
        raise Http404("No such lobby")
    return render(request, "multisweeper/lobby.html", {"lobby_id": lobby_id})

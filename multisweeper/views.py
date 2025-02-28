import uuid

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, redirect

from multisweeper.game.lobby import lobbies, Lobby


def index(request):
    return render(request, "multisweeper/index.html", {"lobbies": lobbies})

def lobby_full(request):
    return render(request, "multisweeper/lobby.html")

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

    if not lobbies[lobby_id].current_players < lobbies[lobby_id].max_players:
        return render(request, "multisweeper/lobby-full.html")

    if not request.user.is_authenticated:
        if 'username' not in request.session:
            return redirect(f'/pick-username/?next=/lobby/{lobby_id}/')

    return render(request, "multisweeper/lobby.html", {
        "lobby_id": lobby_id,
        "lobby": lobbies[lobby_id],
        "mine_count": lobbies[lobby_id].game_instance.mine_count
    })


def pick_username(request):
    if request.method == 'POST':
        username = request.POST.get('username')

        request.session['username'] = username

        next_url = request.GET.get('next', '/')
        return redirect(next_url)

    return render(request, 'multisweeper/pick_username.html')

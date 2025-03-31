import uuid

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect

from multisweeper.forms import LobbySettingsForm
from multisweeper.game.lobby import lobbies, Lobby
from multisweeper.game.lobby_states import LobbyGameInProgressState, LobbyPlayerQuitState
from multisweeper.utils.utils import username_in_player_list


def index(request):
    return render(request, "multisweeper/index.html", {"lobbies": lobbies})


def lobby_full(request):
    return render(request, "multisweeper/lobby-full.html")


def game_in_progress(request):
    return render(request, "multisweeper/game-in-progress.html")


def create_lobby(request):
    if request.method == 'POST':
        form = LobbySettingsForm(request.POST)
        if form.is_valid():
            max_players = form.cleaned_data['max_players']
            mine_count = form.cleaned_data['mine_count']
            ranked = form.cleaned_data['ranked']
            if not request.user.is_authenticated:
                ranked = False  # tylko zarejestrowany uzytkownik moze tworzyc gre rankingowa
            lobby_id = str(uuid.uuid4())
            lobby = Lobby(lobby_id=lobby_id, max_players=max_players, mine_count=mine_count, ranked=ranked)

            lobbies[lobby_id] = lobby
            return redirect(f'/lobby/{lobby_id}')
    elif request.method == 'GET':
        form = LobbySettingsForm()
        return render(request, 'multisweeper/create-lobby.html', {'form': form})
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
        if lobbies[lobby_id].ranked:
            return HttpResponse("Guests can't join ranked games", status=401)

    if isinstance(lobbies[lobby_id].state, LobbyPlayerQuitState):
        scope_user = request.session["username"] if not request.user.is_authenticated else request.user

        if scope_user not in lobbies[lobby_id].players:
            return render(request, "multisweeper/game-in-progress.html")
    else:
        scope_user = request.session["username"] if not request.user.is_authenticated else request.user

        if request.user.is_authenticated:
            if username_in_player_list(scope_user.username, lobbies[lobby_id].players):
                return render(request, "multisweeper/player-already-in-lobby.html")
        else:
            if username_in_player_list(scope_user, lobbies[lobby_id].players):
                return render(request, "multisweeper/player-already-in-lobby.html")

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

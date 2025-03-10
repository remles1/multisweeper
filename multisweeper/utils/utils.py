from typing import Union

from django.contrib.auth.models import User


def username_in_player_list(username: str, players: Union[User | str]):
    for item in players:
        if isinstance(item, str) and item == username:
            return True
        elif isinstance(item, User) and item.username == username:
            return True
    return False

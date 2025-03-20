import json
from typing import TYPE_CHECKING, Union

from django.contrib.auth.models import User

if TYPE_CHECKING:
    from multisweeper.game.lobby import Lobby


def create_message_json(message):
    content = json.dumps({
        "type": "chat_message",
        "message": message
    })
    return content


class ChatManager:
    def __init__(self, lobby: 'Lobby'):
        self.lobby = lobby

    async def process_user_message(self, message: str, sender: Union[User | str]):
        if len(message) <= 140:
            if isinstance(sender, User):
                message_with_username = f"{sender.username}: {message}"
            elif isinstance(sender, str):
                message_with_username = f"{sender}: {message}"
            else:  # not really needed, it's made certain already that sender: User | str
                return
            await self.lobby.broadcast(create_message_json(message_with_username))


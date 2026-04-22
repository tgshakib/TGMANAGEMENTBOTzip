import json
import os
from typing import Any
from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods import TelegramMethod, Response
from aiogram.methods.base import TelegramType

import database as db

STORE_PATH = "admin_msg_ids.json"


def _load() -> list[int]:
    try:
        with open(STORE_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [int(x) for x in data]
    except Exception:
        pass
    return []


def _save(ids: list[int]) -> None:
    try:
        with open(STORE_PATH, "w") as f:
            json.dump(ids, f)
    except Exception:
        pass


_ADMIN_MSG_IDS: list[int] = _load()


def add_id(message_id: int) -> None:
    _ADMIN_MSG_IDS.append(int(message_id))
    _save(_ADMIN_MSG_IDS)


def pop_all() -> list[int]:
    ids = list(_ADMIN_MSG_IDS)
    _ADMIN_MSG_IDS.clear()
    _save(_ADMIN_MSG_IDS)
    return ids


class AdminOutgoingTracker(BaseRequestMiddleware):
    """Tracks every outgoing message sent to the admin chat so we can clean it later."""

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        result = await make_request(bot, method)
        try:
            chat_id = getattr(method, "chat_id", None)
            admin_id = db.get_admin_id()
            if chat_id is not None and int(chat_id) == int(admin_id):
                # Single message result
                mid = getattr(result, "message_id", None)
                if mid:
                    add_id(mid)
                # Media group → list of messages
                elif isinstance(result, list):
                    for m in result:
                        mid = getattr(m, "message_id", None)
                        if mid:
                            add_id(mid)
        except Exception:
            pass
        return result

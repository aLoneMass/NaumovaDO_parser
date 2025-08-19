import csv
import tempfile
from typing import Tuple, Union

from telethon import TelegramClient
from telethon.errors import ChannelPrivateError
from telethon.tl.types import Channel


async def scrape_channel_to_csv(
    client: TelegramClient,
    channel: Union[str, int]
) -> Tuple[str, int, str]:
    """
    Scrape all participants of a public channel (by @username) or a channel the user can access,
    write to a temporary CSV file, and return (file_path, count, channel_title).

    Notes:
    - For private channels, the user account tied to the Telethon session must be a member.
    - For public channels, you can pass the @username string.
    - Passing a numeric ID will only work if the user account can resolve that channel (e.g., is a member or it is in dialogs).
    """
    try:
        entity = await client.get_entity(channel)
    except Exception as exc:
        raise RuntimeError(f"Failed to resolve channel '{channel}': {exc}")

    if not isinstance(entity, Channel):
        raise RuntimeError("Resolved entity is not a Channel. Provide a channel @username or ensure accessibility.")

    title = entity.title or "Unknown Channel"

    # Prepare CSV temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp_path = tmp.name
    tmp.close()

    total = 0

    # Collect participants
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id",
            "username",
            "first_name",
            "last_name",
            "phone",
            "is_bot",
            "lang_code",
        ])

        async for user in client.iter_participants(entity, aggressive=True):
            writer.writerow([
                user.id,
                (user.username or ""),
                (user.first_name or ""),
                (user.last_name or ""),
                (user.phone or ""),
                bool(getattr(user, "bot", False)),
                (getattr(user, "lang_code", None) or ""),
            ])
            total += 1

    return tmp_path, total, title 
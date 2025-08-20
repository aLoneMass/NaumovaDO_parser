import asyncio
import logging
import os
from typing import List

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ChatMemberUpdated, FSInputFile
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.client.default import DefaultBotProperties

from telethon import TelegramClient
from telethon.sessions import StringSession

from scraper import scrape_channel_to_csv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")

admins_raw = os.getenv("ADMINS", "").replace(";", ",")
ADMIN_IDS: List[int] = [int(x.strip()) for x in admins_raw.split(",") if x.strip()]
if not ADMIN_IDS:
    logging.warning("ADMINS is empty. No one will receive the CSV until you set it.")

API_ID = os.getenv("TELEGRAM_API_ID", "").strip()
API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
STRING_SESSION = os.getenv("TELETHON_SESSION", "").strip()

if not API_ID or not API_HASH or not STRING_SESSION:
    logging.warning("Telethon credentials (TELEGRAM_API_ID/TELEGRAM_API_HASH/TELETHON_SESSION) are not fully set. Scraping will fail.")

API_ID_INT = int(API_ID) if API_ID else 0


async def send_to_admins(bot: Bot, file_path: str, caption: str) -> None:
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_document(chat_id=admin_id, document=FSInputFile(file_path), caption=caption)
        except Exception as exc:
            logging.exception(f"Failed to send CSV to admin {admin_id}: {exc}")


async def handle_added_to_channel(event: ChatMemberUpdated, bot: Bot) -> None:
    if event.chat.type != ChatType.CHANNEL:
        return

    new_status = event.new_chat_member.status
    if new_status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER):
        return

    channel_username = (event.chat.username or "").strip()
    channel_identifier = channel_username if channel_username else event.chat.id

    logging.info(f"Scraping channel participants from: {channel_identifier}")

    try:
        async with TelegramClient(StringSession(STRING_SESSION), API_ID_INT, API_HASH) as client:
            if not await client.is_user_authorized():
                raise RuntimeError("Telethon session is not authorized. Regenerate TELETHON_SESSION in .env")
            file_path, total, title = await scrape_channel_to_csv(client, channel_identifier)
    except Exception as exc:
        logging.exception(f"Scraping failed: {exc}")
        return

    caption = f"Канал: {title}\nУчастников: {total}"

    await send_to_admins(bot, file_path, caption)


async def on_start(message: Message) -> None:
    text = [
        "Бот запущен. Добавьте его в канал или используйте /scrape — он выгрузит участников в CSV и пришлёт админам.",
        f"Ваш ID: {message.from_user.id}",
    ]
    await message.answer("\n".join(text))


async def on_scrape(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in ADMIN_IDS:
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажите канал: /scrape @username или /scrape https://t.me/username")
        return

    target = args[1].strip()
    # normalize t.me link → @username
    if target.startswith("https://t.me/") or target.startswith("t.me/"):
        target = "@" + target.split("/")[-1]

    await message.answer("Начинаю сбор участников… это может занять время")

    try:
        async with TelegramClient(StringSession(STRING_SESSION), API_ID_INT, API_HASH) as client:
            if not await client.is_user_authorized():
                await message.answer("Сессия Telethon не авторизована. Пересоздайте TELETHON_SESSION через generate_session.py")
                return
            file_path, total, title = await scrape_channel_to_csv(client, target)
    except Exception as exc:
        logging.exception("Manual scrape failed: %s", exc)
        await message.answer(f"Ошибка: {exc}")
        return

    caption = f"Канал: {title}\nУчастников: {total}"
    try:
        await message.answer_document(FSInputFile(file_path), caption=caption)
    except Exception:
        # Fallback: отправить всем админам
        await send_to_admins(message.bot, file_path, caption)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.register(on_start, CommandStart())
    dp.message.register(on_scrape, Command("scrape"))
    dp.my_chat_member.register(handle_added_to_channel)

    await dp.start_polling(bot, allowed_updates=["message", "my_chat_member"]) 


if __name__ == "__main__":
    asyncio.run(main()) 
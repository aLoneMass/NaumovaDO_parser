import getpass
from telethon import TelegramClient
from telethon.sessions import StringSession


def main() -> None:
    print("This script will generate a Telethon STRING SESSION for your user account.")
    print("You need API ID and API HASH from https://my.telegram.org/apps")
    api_id_str = input("API_ID: ").strip()
    api_hash = input("API_HASH: ").strip()

    api_id = int(api_id_str)

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        client.start()  # will prompt for phone/code/password interactively
        session_str = client.session.save()
        print("\nCopy this value into TELETHON_SESSION in your .env file:")
        print(session_str)


if __name__ == "__main__":
    main() 
"""
export_session.py - Render uchun TELEGRAM_STRING_SESSION ni chiqarib beruvchi skript.
"""
import sys
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from config import Config

def main():
    print("=" * 60)
    print("TELEGRAM SESSISINI STRING_SESSION SHAKLIDA CHIQARISH")
    print("=" * 60)

    session_file = Config.BASE_DIR / f"{Config.SESSION_NAME}.session"
    if not session_file.exists():
        print(f"❌ '{session_file.name}' fayli topilmadi!")
        print("Iltimos, avval kompyuteringizda 'python main.py' ni ishga tushirib Telegramga kiring.")
        return

    try:
        client = TelegramClient(str(Config.BASE_DIR / Config.SESSION_NAME), Config.API_ID, Config.API_HASH)
        client.connect()

        if not client.is_user_authorized():
            print("❌ Sessiya tasdiqlanmagan. Avval kompyuterda login qiling.")
            client.disconnect()
            return

        string_session = StringSession.save(client.session)
        client.disconnect()

        print("\n✅ Sessiya muvaffaqiyatli olindi!\n")
        print("👇 Quyidagi qatorni Render 'Environment Variables' bo'limiga qo'shing:\n")
        print("Key   : TELEGRAM_STRING_SESSION")
        print(f"Value : {string_session}\n")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    main()

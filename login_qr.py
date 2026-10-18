"""
login_qr.py - Telegram akkauntga QR kod orqali (hech qanday SMS va kodsiz) kirish skripti.
Telefonda Telegram -> Sozlamalar -> Qurilmalar -> Qurilmani ulash (Scan QR) orqali kiring.
"""
import os
import sys
import shutil
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
import qrcode

# UTF-8 ni ta'minlash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import Config


async def do_qr_login():
    print("=" * 65)
    print("📲 TELEGRAM AKKAUNTGA QR KOD BILAN KIRISH (KODSIZ VA TEZKOR)")
    print("=" * 65)

    # 1. Eski yaroqsiz sessiya fayllarini tozalash
    for ext in [".session", ".session-journal"]:
        old_file = Config.BASE_DIR / f"{Config.SESSION_NAME}{ext}"
        if old_file.exists():
            try:
                os.remove(old_file)
                print(f"🗑 Eski yaroqsiz fayl tozalandi: {old_file.name}")
            except Exception as e:
                print(f"⚠️ Ogohlantirish: {e}")

    session_target = str(Config.BASE_DIR / Config.SESSION_NAME)
    client = TelegramClient(session_target, Config.API_ID, Config.API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\n✅ Siz allaqachon tizimga kirgansiz! Akkaunt: {me.first_name} (ID: {me.id})")
        await client.disconnect()
        return

    print("\n⏳ Telegram serveridan yangi QR kod olinmoqda...")
    qr_login = await client.qr_login()

    def generate_and_show_qr(url_data: str):
        # 1. Rasm fayli sifatida saqlash
        qr = qrcode.QRCode(border=2)
        qr.add_data(url_data)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_img_path = Config.BASE_DIR / "qr_login.png"
        img.save(str(qr_img_path))

        # 2. Windows ekranida rasmni avtomatik ochish
        try:
            os.startfile(str(qr_img_path))
            print("🖼 QR kod kompyuter ekranida rasm sifatida ochildi (qr_login.png)!")
        except Exception:
            pass

        # 3. Terminalda ham ko'rsatish
        print("\n👇 QR Kod (terminalda ham ko'rsatilmoqda):")
        try:
            qr.print_ascii(invert=True)
        except Exception:
            pass

        print("\n" + "=" * 65)
        print("📱 TELEFONINGIZDA TELEGRAM ILOVASINI OCHING:")
        print("1. 'Sozlamalar' (Настройки / Settings) bo'limiga kiring.")
        print("2. 'Qurilmalar' (Устройства / Devices) bandini tanlang.")
        print("3. 'Qurilmani ulash' (Подключить устройство / Link Desktop Device) tugmasini bosing.")
        print("4. Kamerani ekrandagi QR kodga qarating!")
        print("=" * 65)

    generate_and_show_qr(qr_login.url)

    # Foydalanuvchi skaner qilishini kutish
    user = None
    while user is None:
        try:
            print("\n⏳ QR kod skaner qilinishi kutilmoqda (telefoningiz orqali skanerlang)...")
            user = await qr_login.wait(timeout=45)
        except asyncio.TimeoutError:
            print("⏱ QR kod muddati tugadi. Yangi QR kod yaratilmoqda...")
            await qr_login.recreate()
            generate_and_show_qr(qr_login.url)
        except SessionPasswordNeededError:
            print("\n🔐 Akkauntingizda 2-bosqichli bulut paroli (Two-Step Verification) o'rnatilgan.")
            pwd = input("👉 Iltimos, Telegram 2-bosqichli parolingizni kiriting: ").strip()
            user = await client.sign_in(password=pwd)
            break
        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}")
            break

    if user:
        print("\n" + "=" * 65)
        print(f"🎉 TABRIKLAYMIZ! AKKAUNTINGIZ MUVAFFAQIYATLI ULANDI!")
        print(f"👤 Ism: {user.first_name} {user.last_name or ''}")
        print(f"🆔 Telegram ID: {user.id}")
        print(f"📞 Telefon: {user.phone or 'Mavjud'}")
        print("=" * 65)

        # Sessiya faylini my_ai_userbot papkasiga ham nusxalash
        session_file = Config.BASE_DIR / f"{Config.SESSION_NAME}.session"
        userbot_session_dir = Config.BASE_DIR / "my_ai_userbot"
        if userbot_session_dir.exists() and session_file.exists():
            target_file = userbot_session_dir / "sunnatbek_ai_userbot.session"
            try:
                shutil.copy2(session_file, target_file)
                print(f"📂 Sessiya 'my_ai_userbot' ga ham nusxalandi: {target_file.name}")
            except Exception as ce:
                print(f"⚠️ Nusxalashda ogohlantirish: {ce}")

        # StringSession chiqarish
        string_session = StringSession.save(client.session)
        print("\n📋 RENDER UCHUN TELEGRAM_STRING_SESSION (ixtiyoriy):")
        print("-" * 65)
        print(string_session)
        print("-" * 65)

        # Vaqtinchalik qr rasmini tozalash
        qr_img_path = Config.BASE_DIR / "qr_login.png"
        if qr_img_path.exists():
            try:
                os.remove(qr_img_path)
            except Exception:
                pass

    await client.disconnect()


def main():
    try:
        asyncio.run(do_qr_login())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bekor qilindi.")
    except Exception as e:
        print(f"\n❌ Kutilmagan xatolik: {e}")


if __name__ == "__main__":
    main()

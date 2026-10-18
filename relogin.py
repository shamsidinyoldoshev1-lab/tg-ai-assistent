"""
relogin.py - Eski sessiyani tozalab, yangidan Telegramga kirish skripti.
SMS va Telegram ilovasi orqali kod olishni qo'llab-quvvatlaydi.
"""
import os
import sys
from pathlib import Path
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
)
from telethon.tl.types.auth import SentCodeTypeApp, SentCodeTypeSms
from telethon.tl.functions.auth import ResendCodeRequest
from config import Config


def main():
    print("=" * 60)
    print("TELEGRAM AKKAUNTGA QAYTA KIRISH (RE-LOGIN)")
    print("=" * 60)

    # 1. Eski bekor bo'lgan sessiya fayllarini o'chirish
    for ext in [".session", ".session-journal"]:
        old_file = Config.BASE_DIR / f"{Config.SESSION_NAME}{ext}"
        if old_file.exists():
            try:
                os.remove(old_file)
                print(f"🗑 Eski yaroqsiz fayl tozalandi: {old_file.name}")
            except Exception as e:
                print(f"⚠️ Faylni o'chirishda ogohlantirish: {e}")

    print("\nKirish usulini tanlang:")
    print("1. 📷 QR Kod orqali (KODSIZ! Telefoningiz bilan skanerlab darhol kirish - TAVSIYA ETILADI)")
    print("2. 📱 Telefon raqami va tasdiqlash kodi orqali")
    mode_choice = input("Tanlang (1 yoki 2, standart 1): ").strip()
    if mode_choice in ("1", ""):
        import login_qr
        login_qr.main()
        return

    client = TelegramClient(str(Config.BASE_DIR / Config.SESSION_NAME), Config.API_ID, Config.API_HASH)
    client.connect()

    phone = input("\n📱 Telefon raqamingizni kiriting (masalan: +998958401545): ").strip()
    if not phone:
        print("❌ Telefon raqami kiritilmadi!")
        client.disconnect()
        return

    print("\nKodni qanday qabul qilmoqchisiz?")
    print("1. Telegram ilovasi orqali (tavsiya etiladi - tez va bepul)")
    print("2. SMS orqali (to'g'ridan-to'g'ri telefoningizga SMS)")
    choice = input("Tanlang (1 yoki 2, standart 1): ").strip()
    force_sms = (choice == "2")

    print("\n⏳ Telegramdan kod so'ralmoqda...")
    try:
        sent_code = client.send_code_request(phone, force_sms=force_sms)
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")
        client.disconnect()
        return

    # Qayerga yuborilganini foydalanuvchiga aniq tushuntirish
    if isinstance(sent_code.type, SentCodeTypeApp):
        print("\n📨 Kod TELEGRAM ILOVASIGA jo'natildi!")
        print("👉 Diqqat: Kod botga kelmaydi! Telegramdagi rasmiy 'Telegram' (ko'k belgili) chatga bordi.")
        print("   (Agar SMS orqali olishni xohlasangiz, pastda kod o'rniga 'sms' deb yozing)")
    elif isinstance(sent_code.type, SentCodeTypeSms):
        print(f"\n📩 Kod {phone} raqamingizga SMS xabar qilib jo'natildi! Telefoningizning SMS bo'limini tekshiring.")
    else:
        print(f"\n📩 Kod jo'natildi (Turi: {type(sent_code.type).__name__}).")

    phone_code_hash = sent_code.phone_code_hash

    while True:
        code = input("\n🔢 Tasdiqlash kodini kiriting (yoki SMS olish uchun 'sms' deb yozing): ").strip()
        if not code:
            continue

        if code.lower() == "sms":
            try:
                print("⏳ SMS orqali qayta jo'natish so'ralmoqda...")
                resend = client(ResendCodeRequest(phone=phone, phone_code_hash=phone_code_hash))
                print(f"📩 Kod {phone} raqamingizga SMS orqali jo'natildi! Telefoningizdagi SMS xabarlarni tekshiring.")
                continue
            except Exception as re_err:
                print(f"⚠️ SMS so'rashda ogohlantirish: {re_err}")
                print("Telegram ba'zan darhol SMS yubormaydi, ilovangizni tekshirib ko'ring.")
                continue

        try:
            client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            break
        except SessionPasswordNeededError:
            pwd = input("🔐 Akkauntingizda 2-bosqichli parol (Two-Step Verification) bor. Parolingizni kiriting: ").strip()
            client.sign_in(password=pwd)
            break
        except PhoneCodeInvalidError:
            print("❌ Kiritilgan kod noto'g'ri! Iltimos, tekshirib qaytadan kiriting.")
        except PhoneCodeExpiredError:
            print("❌ Kod muddati o'tib ketdi. Iltimos, skriptni qaytadan ishga tushiring.")
            client.disconnect()
            return
        except Exception as se:
            print(f"❌ Kirishda xatolik: {se}")
            client.disconnect()
            return

    me = client.get_me()
    print("\n" + "=" * 60)
    print(f"✅ Muvaffaqiyatli ulandi! Akkaunt: {me.first_name} (ID: {me.id})")
    print("=" * 60)

    # Yangi StringSession chiqarish
    string_session = StringSession.save(client.session)
    print("\nRENDER UCHUN YANGI TELEGRAM_STRING_SESSION:")
    print("-" * 60)
    print(string_session)
    print("-" * 60)
    print("\nUshbu yangi kalitni Render'dagi 'Environment Variables' ga kiritishingiz mumkin.\n")
    client.disconnect()


if __name__ == "__main__":
    main()

import asyncio
import sys
import os
import html
from aiohttp import web
from config import Config, logger
import db
import cleanup
import reminder
import control_bot
from userbot import start_userbot


async def health_check(request):
    """Render xizmati bot tirikligini bilishi uchun tekshiruv yo'li."""
    return web.Response(text="Bot is running!")


async def start_web_server():
    """Render uchun ochiq veb-port yaratish."""
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Render veb-serveri {port}-portda ishga tushdi.")


async def notify_agent_crash(error: Exception):
    """Agent tizimida kutilmagan og'ir xatolik (crash) yuz berganda adminga xabarnoma yuborish."""
    try:
        bot = control_bot.get_control_bot()
        if bot and Config.ADMIN_USER_ID:
            err_text = (
                "🚨 <b>AGENT TIZIMIDA OG'IR XATOLIK (CRASH)!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ <b>Xatolik turi:</b> <code>{type(error).__name__}</code>\n"
                f"📝 <b>Tafsilot:</b> <code>{html.escape(str(error)[:600])}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ Dastur faoliyati to'xtadi. Iltimos, terminal yoki <code>logs/agent.log</code> faylini tekshiring."
            )
            await bot.send_message(chat_id=Config.ADMIN_USER_ID, text=err_text, parse_mode="HTML")
            await bot.session.close()
    except Exception as be:
        logger.error(f"Crash xabarnomasini yuborishda xatolik: {be}")


async def main():
    logger.info("=" * 55)
    logger.info("Telegram Shaxsiy AI Agent tizimi ishga tushirilmoqda...")
    logger.info("=" * 55)

    # 0. Render uchun veb-portni ochish
    try:
        await start_web_server()
    except Exception as we:
        logger.warning(f"Veb-serverni ochishda ogohlantirish: {we}")

    # 1. Ma'lumotlar bazasini initsializatsiya qilish
    try:
        await db.init_db()
    except Exception as e:
        logger.critical(f"Ma'lumotlar bazasini ishga tushirishda xatolik: {e}")
        await notify_agent_crash(e)
        return

    # 2. Avtomatik tozalash va eslatmalar xizmatini ishga tushirish (orqa fonda)
    cleanup_task = asyncio.create_task(
        cleanup.start_cleanup_scheduler(interval_hours=24)
    )
    reminder_task = asyncio.create_task(
        reminder.start_reminder_scheduler(interval_hours=12)
    )

    # 3. Userbotni ishga tushirish
    userbot_client = None
    try:
        userbot_client = await start_userbot()
    except ValueError as ve:
        logger.error(f"Konfiguratsiya xatosi:\n{ve}")
        logger.info(".env faylini to'ldiring (.env.example namunasiga qarab) va qaytadan ishga tushiring.")
    except Exception as e:
        logger.error(f"Userbot ulanishida kutilmagan xatolik: {e}", exc_info=True)

    if userbot_client:
        logger.info("✅ 1-, 2-, 3-, 4-, 5- va 6-bosqichlar to'liq faol:")
        logger.info("   - Xabarlar va media saqlanmoqda (kiruvchi/chiquvchi/o'chirilgan/tahrirlangan)")
        logger.info("   - Boshqaruv boti faol (/holat, /xulosa, /qidir, /eslatma, /pauza, /davom, /rejim, /ohang, /xavfsizlik, /yoz)")
        logger.info("   - Erkin matn buyruqlari faol (masalan: 'Karimga ayt, ertaga borolmayman')")
        logger.info("   - Claude/Gemini AI: Shaxsiy uslub, few-shot namunalar, 20 ta xabar konteksti")
        logger.info("   - 4 xil javob rejimi: tasdiq (standart), avto, aralash, ochiq")
        logger.info("   - Xavfsizlik filtri: karta, parol, kod, pul, tibbiyot, shartnoma, huquq")
        logger.info("   - Spamdan himoya: daqiqalik limit (RateLimiter), 3-10s kechikish, 'yozmoqda...' holati")
        logger.info("   - Whisper STT: Ovozli xabarlar avtomatik matnga o'girilib javob tayyorlanadi")
        logger.info("   - Eslatmalar: 3 kundan beri javobsiz qolgan xabarlar fon rejimida eslatiladi")
        logger.info("   - 30 kundan eski ma'lumotlar avtomatik tozalanadi")
    else:
        logger.warning(
            "⚠️ Userbot hozircha ulanmagan. Boshqaruv boti (control_bot) mustaqil rejimda ishga tushiriladi."
        )

    # 4. Boshqaruv boti mavjud bo'lsa bitta asyncio loop ichida ishga tushirish
    bot = control_bot.get_control_bot()
    dp = control_bot.get_control_dispatcher()

    tasks = []
    if userbot_client:
        tasks.append(userbot_client.run_until_disconnected())

    if bot:
        logger.info("🤖 Boshqaruv boti faollashtirildi (aiogram 3).")
        tasks.append(dp.start_polling(bot))

        # Adminga ishga tushganlik xabarini yuborish
        if Config.ADMIN_USER_ID:
            try:
                status_note = (
                    "✅ <b>Tizim to'liq faol (Userbot + Bot)</b>"
                    if userbot_client
                    else "⚠️ <i>Eslatma: Userbot akkaunti ulanmagan. Shaxsiy yozishmalarni kuzatish uchun terminalda <code>python relogin.py</code> ni ishga tushiring.</i>"
                )
                startup_msg = (
                    "🚀 <b>Telegram AI Agent boshqaruv boti muvaffaqiyatli ishga tushdi!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"{status_note}\n\n"
                    "💡 <i>Bot buyruqlari:</i> /holat, /rejim, /yoz, /pauza, /davom"
                )
                await bot.send_message(chat_id=Config.ADMIN_USER_ID, text=startup_msg, parse_mode="HTML")
            except Exception as se:
                logger.warning(f"Adminga startup xabarnomasini yuborishda ogohlantirish: {se}")
    else:
        logger.warning(
            "⚠️ TELEGRAM_BOT_TOKEN ko'rsatilmagan. O'chirilgan xabarlar 'Saved Messages' ga yuboriladi."
        )

    if not tasks:
        logger.error("Ishga tushirish uchun xizmat topilmadi. Dastur to'xtatildi.")
        cleanup_task.cancel()
        reminder_task.cancel()
        return

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    except Exception as ge:
        logger.critical(f"Tizim ishlashida xatolik yuz berdi: {ge}", exc_info=True)
        await notify_agent_crash(ge)
    finally:
        cleanup_task.cancel()
        reminder_task.cancel()
        if bot:
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Tizim to'xtatildi.")
    except Exception as e:
        logger.critical(f"Kutilmagan xatolik: {e}", exc_info=True)
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from config import Config, logger

PERSONA_FILE = Config.BASE_DIR / "persona.json"
SAMPLES_FILE = Config.BASE_DIR / "style_samples.json"

_cached_persona: Optional[Dict[str, Any]] = None
_last_mtime: float = 0


def load_persona() -> Dict[str, Any]:
    """persona.json faylidan shaxsiy profil va kontaktlar qoidalarini yuklash."""
    global _cached_persona, _last_mtime

    default_persona = {
        "user_profile": {
            "age": 15,
            "schools": [
                "265-maktabda o'qiyman",
                "Mars IT School da IT va dasturlash bo'yicha o'qiyman",
            ],
            "bio": "Men 15 yoshli o'quvchiman. Toshkentda 265-maktabda va Mars IT Schoolda o'qiyman.",
            "general_rules": [
                "HECH QACHON o'zingni AI, bot, sun'iy intellekt, robot yoki yordamchi deb aytma! Sen aynan shu Telegram profil egasisan.",
                "Har doim 1-shaxs nomidan gapir ('men', 'o'zim', 'bordim', 'darsdaman', 'chiqaman', 'yozaman').",
                "Telegram chat formatida yoz: 1-2 ta qisqa, lo'nda va tabiiy insoniy gap. Uzun rasmiy insho yoki robotdek matnlar yozma.",
                "Suhbatdosh qaysi tilda yozsa, o'sha tilda javob ber (asosan o'zbek tilida).",
                "Xavfsizlik: Pul o'tkazish, bank karta raqami, parol, kod bo'yicha mustaqil va'da berma, 'Hozir darsdaman / bandman, keyinroq gaplashamiz' deb qisqa o'tkazib yubor.",
            ],
        },
        "contact_groups": {
            "kattalar_ustozlar": {
                "name": "O'qituvchilar va Kattalar",
                "keywords": [
                    "nurmuhammad a", "nurmuhammad", "ustoz", "adajonim", "adajon",
                    "onajonim", "onajon", "gulola ustoz", "gulola", "buvijon",
                    "kotta tog'am", "kotta togam", "tog'am", "togam", "aka"
                ],
                "tone_prompt": "Suhbatdosh - ustoz, ota-ona yoki oila kattasi. OHANG: Har doim «Siz»lab, juda odobli, rasmiy va hurmat bilan gapir. Mutlaqo so'kinish, qo'pollik yoki erkalik bo'lmasin. Darslar, topshiriqlar, oilaviy masalalarda andishali, tartibli va qisqa javob ber.",
                "fallbacks": [
                    "Vaalaykum assalom. Hozir darsdaman, chiqib albatta yozaman.",
                    "Assalomu alaykum. Hozir biroz band edim, bo'shab bog'lanaman.",
                ],
            },
            "maktabdoshlar_dostlar": {
                "name": "Maktabdoshlar va Do'stlar",
                "keywords": [
                    "bilol", "abu", "botirjon", "botir", "xumoyun", "humoyun", "muhammadali", "abduazim"
                ],
                "tone_prompt": "Suhbatdosh - maktabdosh, sinfdosh yoki yaqin o'rtoq (tengdosh). OHANG: Erkin, samimiy, do'stona, o'zbekcha yoshlar so'zlashuv tilida ('sen'lab). O'quv jarayonlari, 265-maktab, Mars IT School darslari va uyga vazifalar haqida gaplash. Agar ular so'kib yoki qo'pol hazillashib yozsa, do'stona tarzda ularning ohangiga moslab, teng kelib erkinroq/o'rtoqlardek gap qaytarishing mumkin (o'rtoqlar orasidagi me'yorda).",
                "fallbacks": [
                    "Salom, hozir bandroq edim, ozroqdan keyin yozaman.",
                    "Salom, darsdaman hozir, chiqib gaplashamiz.",
                ],
            },
            "notanishlar": {
                "name": "Notanishlar",
                "keywords": [],
                "tone_prompt": "Suhbatdosh - notanish yoki yangi kontakt. OHANG: Ehtiyotkor, begona gaplarga aralashmasdan, lo'nda va qisqa.",
                "fallbacks": [
                    "Assalomu alaykum, kim bu?",
                    "Assalomu alaykum. Hozir band edim, bo'shab yozaman.",
                ],
            },
        },
    }

    if not PERSONA_FILE.exists():
        try:
            with open(PERSONA_FILE, "w", encoding="utf-8") as f:
                json.dump(default_persona, f, ensure_ascii=False, indent=2)
            _cached_persona = default_persona
            return default_persona
        except Exception as e:
            logger.error(f"persona.json yaratishda xatolik: {e}")
            return default_persona

    try:
        current_mtime = PERSONA_FILE.stat().st_mtime
        if _cached_persona is not None and current_mtime == _last_mtime:
            return _cached_persona

        with open(PERSONA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _cached_persona = data
            _last_mtime = current_mtime
            return data
    except Exception as e:
        logger.error(f"persona.json yuklashda xatolik: {e}")
        return _cached_persona or default_persona


def identify_contact_group(
    contact_name: Optional[str] = None,
    contact_type: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Kontakt nomidan yoki bazadagi turidan kelib chiqib tegishli guruhni aniqlash:
    1. 'kattalar_ustozlar'
    2. 'maktabdoshlar_dostlar'
    3. 'notanishlar'
    """
    persona = load_persona()
    groups = persona.get("contact_groups", {})

    clean_name = (contact_name or "").lower().strip()
    clean_type = (contact_type or "").lower().strip()

    # 1. Kontakt nomidagi kalit so'zlar bo'yicha tekshirish
    if clean_name:
        for group_key in ["kattalar_ustozlar", "maktabdoshlar_dostlar"]:
            group_info = groups.get(group_key, {})
            keywords = [kw.lower() for kw in group_info.get("keywords", [])]
            for kw in keywords:
                if kw in clean_name or clean_name in kw:
                    return group_key, group_info

    # 2. Bazadagi kontakt turiga qarab moslashtirish
    if clean_type in ["kattalar", "ish", "ustoz"]:
        if "kattalar_ustozlar" in groups:
            return "kattalar_ustozlar", groups["kattalar_ustozlar"]
    elif clean_type in ["dostlar", "oila", "sinfdosh", "maktabdosh"]:
        if "maktabdoshlar_dostlar" in groups:
            return "maktabdoshlar_dostlar", groups["maktabdoshlar_dostlar"]

    # 3. Odatiy holat: notanishlar
    default_group = groups.get("notanishlar", {
        "name": "Notanishlar",
        "tone_prompt": "Suhbatdosh - notanish yoki yangi kontakt. Ohang: Ehtiyotkor, begona gaplarga aralashmasdan, lo'nda va qisqa.",
        "fallbacks": ["Assalomu alaykum, kim bu?", "Hozir band edim, bo'shab yozaman."],
    })
    return "notanishlar", default_group


def load_style_samples(category: Optional[str] = None, max_samples: int = 4) -> str:
    """Mos toifadagi yozish namunalarini few-shot tarzida promptga qo'shish."""
    if not SAMPLES_FILE.exists():
        return ""
    try:
        with open(SAMPLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        filtered = [s for s in data if s.get("category") == category]
        if not filtered:
            filtered = [s for s in data if s.get("language") == "uz"][:max_samples]
        else:
            filtered = filtered[:max_samples]
        if not filtered:
            return ""
        lines = ["\nYOZISH USLUBIDAN NAMUNALAR (SHU KABI TABIIY VA QISQA JAVOB BER):"]
        for idx, item in enumerate(filtered, 1):
            dialog = item.get("dialog", [])
            if len(dialog) >= 2:
                lines.append(f"Namuna {idx}:")
                lines.append(f"  Suhbatdosh: «{dialog[0].get('content', '')}»")
                lines.append(f"  Sen: «{dialog[1].get('content', '')}»")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Namunalar faylini o'qishda xatolik: {e}")
        return ""


def build_system_prompt(
    contact_name: Optional[str] = None,
    contact_type: Optional[str] = "notanish",
    is_active_dialog: bool = False,
) -> str:
    """
    Profil egasining shaxsi (15 yosh, 265-maktab, Mars IT School) va
    suhbatdosh guruhiga (kattalar/ustozlar, do'stlar, notanishlar) mos system prompt.
    """
    persona = load_persona()
    profile = persona.get("user_profile", {})
    age = profile.get("age", 15)
    schools = "\n".join([f"- {s}" for s in profile.get("schools", [])])
    rules = "\n".join([f"{i+1}. {r}" for i, r in enumerate(profile.get("general_rules", []))])

    group_key, group_info = identify_contact_group(contact_name=contact_name, contact_type=contact_type)
    group_name = group_info.get("name", "Kontakt")
    tone_instruction = group_info.get("tone_prompt", "")
    samples_block = load_style_samples(category=group_key, max_samples=4)

    if is_active_dialog:
        greeting_instruction = (
            "SALOMLASHISH QOIDASI (JUDA MUHIM):\n"
            "Suhbatdosh bilan oxirgi marta yaqinda (30 daqiqadan kam vaqt ichida) gaplashilgan. Suhbat faol davom etmoqda!\n"
            "- ASLO QAYTA SALOMLASHMA! 'Assalomu alaykum' yoki 'Salom' deb javob berma!\n"
            "- To'g'ridan-to'g'ri berilgan savolga yoki gapga insondek lo'nda javob ber.\n"
            "  Masalan: «Assalomu alaykum buvijon, hammasi yaxshi» deb EMAS, balki «Rahmat buvijon, hammasi yaxshi, uydagilar ham tinchgina yurishibdi» deb javob ber."
        )
    else:
        greeting_instruction = (
            "SALOMLASHISH QOIDASI:\n"
            "Suhbat yangi boshlanmoqda yoki oxirgi xabardan beri 30+ daqiqa o'tgan.\n"
            "- 'Assalomu alaykum' yoki 'Salom' deb salomlashish o'rinli va tabiiy."
        )

    prompt = f"""Sen Telegram akkaunt egasining o'zisan (1-shaxs nomidan gapirasan).
Sen hech qanday AI, bot yoki begona yordamchi EMASSAN. Suhbatdosh sen bilan (akkaunt egasi bilan) gaplashmoqda.

SHAXSIY MA'LUMOTLARING:
- Yoshing: {age} yoshda
- O'qish joylaring:
{schools}

SUHBATDOSH VA MUNOSABAT GURUHI:
- Suhbatdosh: «{contact_name or 'Noma\'lum kontakt'}»
- Guruh: {group_name} ({group_key})
- Ushbu suhbatdosh bilan muloqot qoidasi:
{tone_instruction}

{greeting_instruction}

ENG ASOSIY VA BUZILMAS QOIDALAR:
{rules}

CHAT VA YOZISH FORMATI:
- Telegram xabari formatida: 1-2 gapdan iborat juda qisqa, lo'nda va tabiiy insondek yoz.
- Uzun jumlalar, kitobiy rasmiyatchilik, kirish-chiqish gaplar yoki robotdek jumlalar bo'lmasin.
- Hech qachon o'zingni 'AI', 'bot', 'sun'iy intellekt', 'profil egasi' deb atama!
- Faqat Telegramga yuboriladigan to'g'ridan-to'g'ri tayyor xabar matnini qaytar. Qo'shimcha izoh yoki tirnoqsiz!
{samples_block}
"""
    return prompt.strip()


def sanitize_reply(
    reply: str,
    group_key: str = "notanishlar",
    is_active_dialog: bool = False,
    is_user_greeting: bool = False,
) -> str:
    """
    1. AI agentligini bildiruvchi har qanday jumlalarni tozalash.
    2. Agar suhbat 30 daqiqa ichida davom etayotgan bo'lsa (is_active_dialog) va suhbatdosh salom bermagan bo'lsa,
       har bitta savolda 'Assalomu alaykum' deb qaytaravermaslik uchun boshidagi takroriy salomni olib tashlash.
    """
    if not reply:
        return reply

    clean = reply.strip().strip('"').strip("'")

    # 1. AI agentligini oshkor qiluvchi iboralar ro'yxati
    forbidden_patterns = [
        r"men\s+profil\s+egasining\s+ai\s+agentiman[.,!]?",
        r"men\s+ai\s+agentiman[.,!]?",
        r"ai\s+agent[.,!]?",
        r"ai\s+yordamchi[.,!]?",
        r"sun'iy\s+intellekt[.,!]?",
        r"profil\s+egasiga\s+yetkazib\s+qo'yaman[.,!]?",
        r"profil\s+egasiga\s+yetkazaman[.,!]?",
        r"akkaunt\s+egasi[.,!]?",
        r"men\s+botman[.,!]?",
    ]

    for pat in forbidden_patterns:
        clean = re.sub(pat, "", clean, flags=re.IGNORECASE).strip()

    # 2. Agar suhbat 30 daqiqa ichida davom etayotgan bo'lsa va foydalanuvchi salom bermagan bo'lsa,
    # boshidagi ortiqcha 'Assalomu alaykum' / 'Salom' ni tozalash
    if is_active_dialog and not is_user_greeting:
        clean = re.sub(
            r"^(assalomu\s+alaykum|assalomu\s+alekom|asalomu\s+alaykum|vaalaykum\s+assalom|salom)\s*[,!.]?\s*",
            "",
            clean,
            flags=re.IGNORECASE
        ).strip()
        if clean:
            clean = clean[0].upper() + clean[1:]

    # Bo'shab qolgan bo'lsa yoki buzilgan bo'lsa, zaxiradan olamiz
    if len(clean) < 2:
        return get_fallback_reply("", group_key, is_active_dialog=is_active_dialog)

    # Tinish belgilaridan keyingi ortiqcha bo'shliqlarni to'g'rilash
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def get_fallback_reply(incoming_text: str, group_key: str = "notanishlar", is_active_dialog: bool = False) -> str:
    """Offline yoki API xatoligida insoniy zaxira javoblar."""
    persona = load_persona()
    groups = persona.get("contact_groups", {})
    group_info = groups.get(group_key, {})
    fallbacks = group_info.get("fallbacks", [])

    text_lower = incoming_text.lower().strip()

    if group_key == "kattalar_ustozlar":
        if is_active_dialog:
            return "Rahmat, hammasi yaxshi, tinchgina."
        if any(s in text_lower for s in ["assalomu", "asalomu", "салом", "salom"]):
            return "Vaalaykum assalom. Hozir darsdaman, chiqib albatta yozaman."
        return "Assalomu alaykum. Hozir darsdaman, bo'shab bog'lanaman."

    elif group_key == "maktabdoshlar_dostlar":
        if is_active_dialog:
            return "Bo'ldi, tushundim. Ozroqdan keyin yozaman."
        if any(s in text_lower for s in ["salom", "qales", "qaleysan", "nima gap"]):
            return "Salom, nima gap? Hozir bandroq edim, ozroqdan keyin yozaman."
        return "Hozir darsdaman, chiqib gaplashamiz."

    else:
        if is_active_dialog:
            return "Tushundim, ma'lumotni oldim."
        if any(s in text_lower for s in ["assalomu", "asalomu", "salom"]):
            return "Assalomu alaykum, kim bu?"
        return "Assalomu alaykum. Hozir band edim, bo'shab yozaman."

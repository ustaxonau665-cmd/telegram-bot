import asyncio
import os
import re
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Namuna uchun xavfsiz (whitelist) va xavfli (blacklist) domenlar
SAFE_DOMAINS = {
    "google.com",
    "www.google.com",
    "wikipedia.org",
    "www.wikipedia.org",
    "github.com",
    "t.me",
    "telegram.org",
}

DANGEROUS_DOMAINS = {
    "phishing-example.com",
    "malware-test.ru",
    "free-crypto-scam.xyz",
}

# Xavfli kalit so'zlar (qo'shimcha tekshiruv uchun)
SUSPICIOUS_KEYWORDS = ("free-money", "steal", "hack-account", "phish")

URL_REGEX = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)

dp = Dispatcher()


def normalize_domain(raw_url: str):
    url = raw_url.strip().rstrip(".,!?;:)\"]'")
    if url.lower().startswith("www."):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower()
        if domain.startswith("www."):
            domain_no_www = domain[4:]
        else:
            domain_no_www = domain
        return domain, domain_no_www
    except Exception:
        return "", ""


def check_link_safety(raw_url: str) -> str:
    domain, domain_no_www = normalize_domain(raw_url)
    lower_url = raw_url.lower()

    if domain in DANGEROUS_DOMAINS or domain_no_www in DANGEROUS_DOMAINS:
        return "dangerous"

    if any(word in lower_url for word in SUSPICIOUS_KEYWORDS):
        return "dangerous"

    if domain in SAFE_DOMAINS or domain_no_www in SAFE_DOMAINS:
        return "safe"

    return "unknown"


@dp.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, bot: Bot):
    bot_info = await bot.get_me()
    add_group_url = f"https://t.me/{bot_info.username}?startgroup=true"
    add_channel_url = f"https://t.me/{bot_info.username}?startchannel=true"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Guruhga qo‘shish", url=add_group_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Kanalga qo‘shish", url=add_channel_url
                )
            ],
        ]
    )

    text = (
        "👋 **Assalomu alaykum! Xush kelibsiz!**\n\n"
        "📜 **Botdan foydalanish shartlari:**\n"
        "1️⃣ Bot guruh va kanallarda havolalar (linklar) xavfsizligini nazorat qiladi.\n"
        "2️⃣ Xavfli deb topilgan havolalar darhol o‘chiriladi ⚠️.\n"
        "3️⃣ Xavfsiz havolalar guruhda qoldiriladi ✅.\n"
        "4️⃣ To‘liq ishlashi uchun botga **Administrator** huquqi berilishi kerak 🛡️.\n\n"
        "🚀 Botni guruh yoki kanalingizga qo‘shish uchun quyidagi tugmalardan foydalaning:"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@dp.my_chat_member()
async def on_my_chat_member_update(event: ChatMemberUpdated):
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    was_in_chat = old_status in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.RESTRICTED,
    }
    is_now_in_chat = new_status in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }

    if not was_in_chat and is_now_in_chat:
        if new_status == ChatMemberStatus.ADMINISTRATOR:
            await event.answer(
                "👋 **Assalomu alaykum!** Men guruhga qo‘shildim va darhol **Administrator** bo‘ldim! 🛡️\n"
                "✅ Xizmatga to‘liq tayyorman — xavfli havolalarni nazorat qilaman!"
            )
        else:
            await event.answer(
                "👋 **Assalomu alaykum!** Guruhga qo‘shganingiz uchun rahmat! 😊\n"
                "🔑 Xabarlarni boshqarish va xavfli linklarni o‘chirishim uchun meni **Administrator** qilib tayinlashingizni so‘rayman!"
            )
        return

    if old_status != ChatMemberStatus.ADMINISTRATOR and new_status == ChatMemberStatus.ADMINISTRATOR:
        await event.answer(
            "🎉 **Rahmat, meni Administrator qildingiz!** 🛡️\n"
            "🚀 Men to‘liq **xizmatga tayyorman**! Endi guruhdagi barcha havolalarni tekshirib boraman."
        )


@dp.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def check_group_links(message: Message):
    urls = URL_REGEX.findall(message.text)
    if not urls:
        return

    statuses = [check_link_safety(u) for u in urls]

    if "dangerous" in statuses:
        try:
            await message.delete()
        except Exception:
            await message.reply(
                "⚠️ **Xavfli havola aniqlandi!** Lekin uni o‘chirish uchun menda yetarli admin huquqi yo‘q ❌."
            )
            return

        await message.answer(
            f"🚨 **Xavfli link aniqlandi va o‘chirildi!** 🗑️\n"
            f"👤 Yuboruvchi: {message.from_user.full_name if message.from_user else 'Foydalanuvchi'}\n"
            f"🛡️ Guruh xavfsizligi saqlandi."
        )
        return

    if all(s == "safe" for s in statuses):
        await message.reply(
            "✅ **Xavfsiz link!** Havola o‘chirilmadi, bemalol ko‘rishingiz mumkin 🔗✨"
        )
        return

    await message.reply(
        "🔎 **Havola tekshirildi:** Bu manba hozircha tasdiqlangan ro‘yxatda yo‘q, ehtiyot bo‘ling ⚠️🔗"
    )


async def main():
    bot = Bot(token=BOT_TOKEN)
    print("Bot ishga tushdi...")
    await dp.start_polling(
        bot,
        allowed_updates=["message", "my_chat_member"],
    )


if __name__ == "__main__":
    asyncio.run(main())

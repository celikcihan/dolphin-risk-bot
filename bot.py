#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import re
import unicodedata
import logging
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ApplicationHandlerStop,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("dolphin-transparency-bot")


BOT_TOKEN = os.getenv("BOT_TOKEN", "")

PROJECT_NAME = os.getenv("PROJECT_NAME", "DOLPHIN")

TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS", "0x985fE8B33da494d7fE595B054590d9Eac576b2d1")
VESTING_ADDRESS = os.getenv("VESTING_ADDRESS", "0x5F11428fEe257635A58ea5041688599689aEE123")
SAFE_ADDRESS = os.getenv("SAFE_ADDRESS", "0xaE1B8995D651B2929FC8D8B9929308bf37D1Fbf2")
OWNER_ADDRESS = os.getenv("OWNER_ADDRESS", "0x556E306e0C5e9E27a59096A43ac8664C4f92FC0f")

TOTAL_SUPPLY = int(os.getenv("TOTAL_SUPPLY", "499999999"))
LOCKED_SUPPLY = int(os.getenv("LOCKED_SUPPLY", "200000000"))

PAIR_ADDRESS = os.getenv("PAIR_ADDRESS", "0x5Ed3Bf18f8368785446B43bF416f5dFb34Ec3e22")
TEAM_FINANCE_LOCK_ADDRESS = os.getenv("TEAM_FINANCE_LOCK_ADDRESS", "0x4F0Fd563BE89ec8C3e7D595bf3639128C0a7C33A")
TEAM_FINANCE_LOCK_TX = os.getenv("TEAM_FINANCE_LOCK_TX", "0x601058e3685e1c4050844411b9eec846bc51b528c89c3170ee5074ba688e3a21")
DEXSCREENER_PAIR = os.getenv("DEXSCREENER_PAIR", f"https://dexscreener.com/base/{PAIR_ADDRESS}")
LP_LOCK_UNLOCK_DATE_EN = os.getenv("LP_LOCK_UNLOCK_DATE_EN", "June 13, 2028")
LP_LOCK_UNLOCK_DATE_TR = os.getenv("LP_LOCK_UNLOCK_DATE_TR", "13 Haziran 2028")
INITIAL_LP_DESCRIPTION_EN = os.getenv("INITIAL_LP_DESCRIPTION_EN", "100,000,000 DOLPHIN + 3,800 USDC")
INITIAL_LP_DESCRIPTION_TR = os.getenv("INITIAL_LP_DESCRIPTION_TR", "100,000,000 DOLPHIN + 3,800 USDC")

WEBSITE = os.getenv("WEBSITE", "https://dolphin-trust-dao.lovable.app/")
TELEGRAM = os.getenv("TELEGRAM", "https://t.me/DolphinTokenTurkiye")
X_LINK = os.getenv("X", "https://x.com/xdolphintoken")

BASESCAN_TOKEN = os.getenv(
    "BASESCAN_TOKEN",
    f"https://basescan.org/address/{TOKEN_ADDRESS}",
)
BASESCAN_VESTING = os.getenv(
    "BASESCAN_VESTING",
    f"https://basescan.org/address/{VESTING_ADDRESS}",
)
BASESCAN_SAFE = os.getenv(
    "BASESCAN_SAFE",
    f"https://basescan.org/address/{SAFE_ADDRESS}",
)
BASESCAN_PAIR = os.getenv(
    "BASESCAN_PAIR",
    f"https://basescan.org/address/{PAIR_ADDRESS}",
)
BASESCAN_LOCK = os.getenv(
    "BASESCAN_LOCK",
    f"https://basescan.org/address/{TEAM_FINANCE_LOCK_ADDRESS}",
)
BASESCAN_LOCK_TX = os.getenv(
    "BASESCAN_LOCK_TX",
    f"https://basescan.org/tx/{TEAM_FINANCE_LOCK_TX}",
)

TR_GROUP_ID = int(os.getenv("TR_GROUP_ID", "0"))
GLOBAL_GROUP_ID = int(os.getenv("GLOBAL_GROUP_ID", "0"))

BAD_WORDS_RAW = os.getenv("BAD_WORDS", "")
BAD_WORDS = [
    word.strip()
    for word in BAD_WORDS_RAW.split(",")
    if word.strip()
]
BAD_WORD_WARN = os.getenv("BAD_WORD_WARN", "false").lower() == "true"
BAD_WORD_WARNING_TEXT = os.getenv(
    "BAD_WORD_WARNING_TEXT",
    "⚠️ Please keep the chat respectful. / Lütfen sohbet dilimize dikkat edelim.",
)

MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "false").lower() == "true"
AUTO_DELETE_LINKS = os.getenv("AUTO_DELETE_LINKS", "false").lower() == "true"
LINK_WARN = os.getenv("LINK_WARN", "false").lower() == "true"
LINK_WARNING_TEXT = os.getenv(
    "LINK_WARNING_TEXT",
    "⚠️ Links are not allowed in this group. / Bu grupta link paylaşımı yasaktır.",
)
ALLOWED_LINK_DOMAINS_RAW = os.getenv("ALLOWED_LINK_DOMAINS", "")
ALLOWED_LINK_DOMAINS = {
    domain.strip().casefold().removeprefix("www.")
    for domain in ALLOWED_LINK_DOMAINS_RAW.split(",")
    if domain.strip()
}
URL_REGEX = re.compile(r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)", re.IGNORECASE)


def normalize_for_filter(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"[^a-z0-9ğüşıöç]+", " ", text)
    return " ".join(text.split())


def contains_bad_word(text: str) -> bool:
    if not BAD_WORDS:
        return False

    normalized_text = normalize_for_filter(text)
    compact_text = normalized_text.replace(" ", "")

    for word in BAD_WORDS:
        normalized_word = normalize_for_filter(word)
        if not normalized_word:
            continue

        compact_word = normalized_word.replace(" ", "")

        if re.search(rf"(^|\s){re.escape(normalized_word)}($|\s)", normalized_text):
            return True

        if compact_word and compact_word in compact_text:
            return True

    return False


def extract_link_domains(text: str) -> set[str]:
    domains: set[str] = set()

    for match in URL_REGEX.findall(text or ""):
        raw = match.strip().rstrip(".,);]")
        url = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"

        try:
            domain = urlparse(url).netloc.casefold().removeprefix("www.")
            if domain:
                domains.add(domain)
        except Exception:
            continue

    return domains


def contains_blocked_link(text: str) -> bool:
    if not AUTO_DELETE_LINKS:
        return False

    domains = extract_link_domains(text)

    if not domains:
        return False

    if not ALLOWED_LINK_DOMAINS:
        return True

    for domain in domains:
        allowed = any(domain == allowed_domain or domain.endswith(f".{allowed_domain}") for allowed_domain in ALLOWED_LINK_DOMAINS)
        if not allowed:
            return True

    return False


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user:
        return False

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in {"administrator", "creator"}
    except Exception as e:
        logger.warning("Admin check failed: %s", e)
        return False


def short_addr(addr: str) -> str:
    if not addr or len(addr) < 12:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def is_tr_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == TR_GROUP_ID)


def is_global_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == GLOBAL_GROUP_ID)


def welcome_text_en() -> str:
    return (
        "🐬 Welcome to DOLPHIN\n\n"
        "The official Transparency & Information Bot for the DOLPHIN ecosystem.\n\n"
        "Built on Base Network.\n"
        "Protected by Safe Multisig.\n"
        "Powered by community.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🇺🇸 English Commands\n"
        "/help\n\n"
        "🇹🇷 Türkçe Komutlar\n"
        "/helptr\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🔒 200M Locked Vesting\n"
        "🔐 100% LP Locked until June 13, 2028\n"
        "🛡️ 3/3 Safe Multisig\n"
        "📜 Verified Smart Contracts\n\n"
        f"Website:\n{WEBSITE}\n\n"
        f"Telegram:\n{TELEGRAM}"
    )


def welcome_text_tr() -> str:
    return (
        "🐬 DOLPHIN'e Hoş Geldiniz\n\n"
        "DOLPHIN ekosisteminin resmi Şeffaflık ve Bilgilendirme Botu.\n\n"
        "Base Network üzerinde çalışır.\n"
        "Safe Multisig ile korunur.\n"
        "Topluluk tarafından desteklenir.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🇹🇷 Türkçe Komutlar\n"
        "/helptr\n\n"
        "🇺🇸 English Commands\n"
        "/help\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🔒 200M Kilitli Vesting\n"
        "🔐 LP'nin %100'ü 13 Haziran 2028'e kadar kilitli\n"
        "🛡️ 3/3 Safe Multisig\n"
        "📜 Doğrulanmış Akıllı Kontratlar\n\n"
        f"Website:\n{WEBSITE}\n\n"
        f"Telegram:\n{TELEGRAM}"
    )


def welcome_text_bilingual() -> str:
    return (
        "🐬 Welcome to DOLPHIN / DOLPHIN'e Hoş Geldiniz\n\n"
        "Official Transparency & Information Bot.\n"
        "Resmi Şeffaflık ve Bilgilendirme Botu.\n\n"
        "🔒 200M Locked Vesting / 200M Kilitli Vesting\n"
        "🔐 100% LP Locked until June 2028 / LP %100 kilitli\n"
        "🛡️ 3/3 Safe Multisig\n"
        "📜 Verified Smart Contracts / Doğrulanmış Kontratlar\n\n"
        "🇺🇸 English Commands:\n"
        "/help\n\n"
        "🇹🇷 Türkçe Komutlar:\n"
        "/helptr"
    )


def help_text_en() -> str:
    return (
        "🐬 DOLPHIN Commands\n\n"
        "/risk - Project risk report\n"
        "/vesting - Vesting information\n"
        "/locked - Locked token status\n"
        "/supply - Total supply\n"
        "/tokenomics - Token allocation\n"
        "/contracts - Contract addresses\n"
        "/safe - Safe multisig information\n"
        "/owner - Contract owner information\n"
        "/verify - Verification status\n"
        "/links - Official links\n"
        "/about - About DOLPHIN\n"
        "/chatid - Show current chat ID"
    )


def help_text_tr() -> str:
    return (
        "🐬 DOLPHIN Komutları\n\n"
        "/risktr - Proje risk raporu\n"
        "/vestingtr - Vesting bilgileri\n"
        "/lockedtr - Kilitli token durumu\n"
        "/supplytr - Toplam arz\n"
        "/tokenomicstr - Token dağılımı\n"
        "/contractstr - Kontrat adresleri\n"
        "/safetr - Safe multisig bilgisi\n"
        "/ownertr - Kontrat sahibi bilgisi\n"
        "/verifytr - Doğrulama durumu\n"
        "/linkstr - Resmi bağlantılar\n"
        "/abouttr - DOLPHIN hakkında\n"
        "/chatid - Grup ID bilgisini gösterir"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    if is_tr_chat(update):
        text = welcome_text_tr()
    elif is_global_chat(update):
        text = welcome_text_en()
    else:
        text = welcome_text_bilingual()

    await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(help_text_en(), disable_web_page_preview=True)


async def help_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(help_text_tr(), disable_web_page_preview=True)


async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🐬 DOLPHIN Risk & Transparency Report\n\n"
        "✅ Token contract verified\n"
        "✅ Vesting contract verified\n"
        "✅ 200,000,000 DOLPHIN locked\n"
        "✅ Safe Multisig created\n"
        "✅ No mint function\n"
        "✅ No blacklist\n"
        "✅ No max wallet\n"
        "✅ No max transaction\n"
        "✅ Trading is live\n"
        "✅ Liquidity is open on Uniswap V2\n"
        "✅ 100% LP locked via Team Finance until June 13, 2028\n\n"
        "🔒 Locked Vesting\n"
        "Amount: 200,000,000 DOLPHIN\n"
        "Cliff: 12 months\n"
        "Vesting: 36 months\n"
        "Current releasable amount: 0 DOLPHIN\n\n"
        "🛡️ Safe Multisig\n"
        f"{SAFE_ADDRESS}\n\n"
        "📜 Token Contract\n"
        f"{TOKEN_ADDRESS}\n\n"
        "LP Pair:\n"
        f"{PAIR_ADDRESS}\n\n"
        "Team Finance Lock:\n"
        f"{TEAM_FINANCE_LOCK_ADDRESS}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def risk_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🐬 DOLPHIN Risk ve Şeffaflık Raporu\n\n"
        "✅ Token kontratı doğrulandı\n"
        "✅ Vesting kontratı doğrulandı\n"
        "✅ 200,000,000 DOLPHIN kilitli\n"
        "✅ Safe Multisig oluşturuldu\n"
        "✅ Mint fonksiyonu yok\n"
        "✅ Blacklist yok\n"
        "✅ Max wallet yok\n"
        "✅ Max transaction yok\n"
        "✅ Trading açık\n"
        "✅ Likidite Uniswap V2 üzerinde açık\n"
        "✅ LP\'nin %100\'ü Team Finance üzerinden 13 Haziran 2028\'e kadar kilitli\n\n"
        "🔒 Kilitli Vesting\n"
        "Miktar: 200,000,000 DOLPHIN\n"
        "Cliff: 12 ay\n"
        "Vesting: 36 ay\n"
        "Şu an kullanılabilir miktar: 0 DOLPHIN\n\n"
        "🛡️ Safe Multisig\n"
        f"{SAFE_ADDRESS}\n\n"
        "📜 Token Kontratı\n"
        f"{TOKEN_ADDRESS}\n\n"
        "LP Pair:\n"
        f"{PAIR_ADDRESS}\n\n"
        "Team Finance Lock:\n"
        f"{TEAM_FINANCE_LOCK_ADDRESS}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def vesting_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔒 DOLPHIN Vesting Information\n\n"
        "Locked amount:\n"
        "200,000,000 DOLPHIN\n\n"
        "Schedule:\n"
        "12-month cliff\n"
        "36-month vesting\n\n"
        "Current released:\n"
        "0 DOLPHIN\n\n"
        "Current releasable:\n"
        "0 DOLPHIN\n\n"
        "Beneficiary:\n"
        "DOLPHIN Safe Multisig\n"
        f"{SAFE_ADDRESS}\n\n"
        "Vesting Contract:\n"
        f"{VESTING_ADDRESS}\n\n"
        f"BaseScan:\n{BASESCAN_VESTING}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def vesting_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔒 DOLPHIN Vesting Bilgileri\n\n"
        "Kilitli miktar:\n"
        "200,000,000 DOLPHIN\n\n"
        "Plan:\n"
        "12 ay cliff\n"
        "36 ay vesting\n\n"
        "Şu ana kadar açılan:\n"
        "0 DOLPHIN\n\n"
        "Şu an kullanılabilir:\n"
        "0 DOLPHIN\n\n"
        "Beneficiary:\n"
        "DOLPHIN Safe Multisig\n"
        f"{SAFE_ADDRESS}\n\n"
        "Vesting Kontratı:\n"
        f"{VESTING_ADDRESS}\n\n"
        f"BaseScan:\n{BASESCAN_VESTING}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def locked_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔐 Locked Token Status\n\n"
        f"Total Supply: {TOTAL_SUPPLY:,} DOLPHIN\n"
        f"Locked Supply: {LOCKED_SUPPLY:,} DOLPHIN\n"
        "Locked Share: 40%\n\n"
        "Status:\n"
        "✅ 200M locked in verified vesting contract\n"
        "✅ Current releasable vesting amount: 0 DOLPHIN\n"
        "✅ 100% LP locked via Team Finance until June 13, 2028\n"
        "✅ Beneficiary: Safe Multisig\n\n"
        "LP Lock:\n"
        f"{BASESCAN_LOCK}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def locked_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔐 Kilitli Token Durumu\n\n"
        f"Toplam Arz: {TOTAL_SUPPLY:,} DOLPHIN\n"
        f"Kilitli Miktar: {LOCKED_SUPPLY:,} DOLPHIN\n"
        "Kilitli Oran: %40\n\n"
        "Durum:\n"
        "✅ 200M doğrulanmış vesting kontratında kilitli\n"
        "✅ Şu an kullanılabilir vesting miktarı: 0 DOLPHIN\n"
        "✅ LP'nin %100'ü Team Finance üzerinden 13 Haziran 2028'e kadar kilitli\n"
        "✅ Beneficiary: Safe Multisig\n\n"
        "LP Kilidi:\n"
        f"{BASESCAN_LOCK}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def supply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 DOLPHIN Supply\n\n"
        f"Total Supply: {TOTAL_SUPPLY:,} DOLPHIN\n"
        "Mintable: No\n"
        "Burnable: Yes\n\n"
        "The supply is fixed. No additional DOLPHIN can be minted."
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def supply_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 DOLPHIN Arz Bilgisi\n\n"
        f"Toplam Arz: {TOTAL_SUPPLY:,} DOLPHIN\n"
        "Mint: Yok\n"
        "Burn: Var\n\n"
        "Arz sabittir. Sonradan ek DOLPHIN basılamaz."
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def tokenomics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 DOLPHIN Tokenomics\n\n"
        "🔒 Locked Vesting: 200,000,000 (40%)\n"
        "💧 Initial LP: 100,000,000 (20%)\n"
        "🔥 Burn Reserve: 90,000,000 (18%)\n"
        "🤝 Supporters: 40,000,000 (8%)\n"
        "👥 Team: 30,000,000 (6%)\n"
        "📢 Marketing: 20,000,000 (4%)\n"
        "💻 Webmaster: 10,000,000 (2%)\n"
        "🧩 Operations Reserve: 9,999,999 (2%)\n\n"
        "Initial LP opened with 100,000,000 DOLPHIN + 3,800 USDC.\n"
        "100% of LP is locked via Team Finance until June 13, 2028.\n\n"
        "Total Supply: 499,999,999 DOLPHIN"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def tokenomics_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 DOLPHIN Token Dağılımı\n\n"
        "🔒 Kilitli Vesting: 200,000,000 (%40)\n"
        "💧 İlk LP: 100,000,000 (%20)\n"
        "🔥 Yakım Rezervi: 90,000,000 (%18)\n"
        "🤝 Destekçiler: 40,000,000 (%8)\n"
        "👥 Ekip: 30,000,000 (%6)\n"
        "📢 Pazarlama: 20,000,000 (%4)\n"
        "💻 Webmaster: 10,000,000 (%2)\n"
        "🧩 Operasyon Rezervi: 9,999,999 (%2)\n\n"
        "İlk LP 100,000,000 DOLPHIN + 3,800 USDC ile açıldı.\n"
        "LP'nin %100'ü Team Finance üzerinden 13 Haziran 2028'e kadar kilitli.\n\n"
        "Toplam Arz: 499,999,999 DOLPHIN"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def contracts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📜 DOLPHIN Contracts\n\n"
        "Token Contract:\n"
        f"{TOKEN_ADDRESS}\n"
        f"{BASESCAN_TOKEN}\n\n"
        "Vesting Contract:\n"
        f"{VESTING_ADDRESS}\n"
        f"{BASESCAN_VESTING}\n\n"
        "Safe Multisig:\n"
        f"{SAFE_ADDRESS}\n"
        f"{BASESCAN_SAFE}\n\n"
        "Uniswap V2 LP Pair:\n"
        f"{PAIR_ADDRESS}\n"
        f"{BASESCAN_PAIR}\n\n"
        "Team Finance LP Lock:\n"
        f"{TEAM_FINANCE_LOCK_ADDRESS}\n"
        f"{BASESCAN_LOCK}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def contracts_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📜 DOLPHIN Kontratları\n\n"
        "Token Kontratı:\n"
        f"{TOKEN_ADDRESS}\n"
        f"{BASESCAN_TOKEN}\n\n"
        "Vesting Kontratı:\n"
        f"{VESTING_ADDRESS}\n"
        f"{BASESCAN_VESTING}\n\n"
        "Safe Multisig:\n"
        f"{SAFE_ADDRESS}\n"
        f"{BASESCAN_SAFE}\n\n"
        "Uniswap V2 LP Pair:\n"
        f"{PAIR_ADDRESS}\n"
        f"{BASESCAN_PAIR}\n\n"
        "Team Finance LP Lock:\n"
        f"{TEAM_FINANCE_LOCK_ADDRESS}\n"
        f"{BASESCAN_LOCK}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def safe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🛡️ DOLPHIN Safe Multisig\n\n"
        "Safe Address:\n"
        f"{SAFE_ADDRESS}\n\n"
        "Current setup:\n"
        "3 signers / 3 approvals\n\n"
        "Purpose:\n"
        "Treasury, ownership and project governance security.\n\n"
        f"BaseScan:\n{BASESCAN_SAFE}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def safe_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🛡️ DOLPHIN Safe Multisig\n\n"
        "Safe Adresi:\n"
        f"{SAFE_ADDRESS}\n\n"
        "Mevcut yapı:\n"
        "3 imzacı / 3 onay\n\n"
        "Amaç:\n"
        "Treasury, ownership ve proje güvenliği.\n\n"
        f"BaseScan:\n{BASESCAN_SAFE}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👤 DOLPHIN Contract Owner\n\n"
        "Current owner:\n"
        f"{OWNER_ADDRESS}\n\n"
        "Planned governance:\n"
        "Ownership will be transferred to the DOLPHIN Safe Multisig after launch operations are completed.\n\n"
        f"Safe:\n{SAFE_ADDRESS}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def owner_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👤 DOLPHIN Kontrat Sahibi\n\n"
        "Mevcut owner:\n"
        f"{OWNER_ADDRESS}\n\n"
        "Planlanan yönetişim:\n"
        "Launch operasyonları tamamlandıktan sonra ownership DOLPHIN Safe Multisig'e devredilecektir.\n\n"
        f"Safe:\n{SAFE_ADDRESS}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "✅ DOLPHIN Verification Status\n\n"
        "Token Contract:\n"
        "Verified on BaseScan ✅\n\n"
        "Vesting Contract:\n"
        "Verified on BaseScan ✅\n\n"
        "Transparency:\n"
        "Source code is public and readable on BaseScan.\n\n"
        f"Token:\n{BASESCAN_TOKEN}\n\n"
        f"Vesting:\n{BASESCAN_VESTING}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def verify_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "✅ DOLPHIN Doğrulama Durumu\n\n"
        "Token Kontratı:\n"
        "BaseScan üzerinde doğrulandı ✅\n\n"
        "Vesting Kontratı:\n"
        "BaseScan üzerinde doğrulandı ✅\n\n"
        "Şeffaflık:\n"
        "Kaynak kodlar BaseScan üzerinde herkese açık ve okunabilir durumdadır.\n\n"
        f"Token:\n{BASESCAN_TOKEN}\n\n"
        f"Vesting:\n{BASESCAN_VESTING}"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = [
        "🔗 Official DOLPHIN Links",
        "",
        f"Website: {WEBSITE}",
        f"Telegram: {TELEGRAM}",
    ]
    if X_LINK:
        lines.append(f"X: {X_LINK}")

    lines.extend([
        "",
        f"Token Contract: {BASESCAN_TOKEN}",
        f"Vesting Contract: {BASESCAN_VESTING}",
        f"DEX Screener: {DEXSCREENER_PAIR}",
        f"Team Finance LP Lock: {BASESCAN_LOCK}",
    ])

    if update.effective_message:
        await update.effective_message.reply_text("\n".join(lines), disable_web_page_preview=True)


async def links_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = [
        "🔗 Resmi DOLPHIN Bağlantıları",
        "",
        f"Website: {WEBSITE}",
        f"Telegram: {TELEGRAM}",
    ]
    if X_LINK:
        lines.append(f"X: {X_LINK}")

    lines.extend([
        "",
        f"Token Kontratı: {BASESCAN_TOKEN}",
        f"Vesting Kontratı: {BASESCAN_VESTING}",
        f"DEX Screener: {DEXSCREENER_PAIR}",
        f"Team Finance LP Kilidi: {BASESCAN_LOCK}",
    ])

    if update.effective_message:
        await update.effective_message.reply_text("\n".join(lines), disable_web_page_preview=True)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🐬 About DOLPHIN\n\n"
        "DOLPHIN is a community-driven ERC-20 token deployed on Base Mainnet.\n\n"
        "It was deployed directly with a custom smart contract, not through Zora or token generator platforms.\n\n"
        "Core transparency points:\n"
        "✅ Verified contracts\n"
        "✅ 200M locked vesting\n"
        "✅ 100% LP locked until June 13, 2028\n"
        "✅ Safe Multisig governance\n"
        "✅ Fixed supply\n"
        "✅ No mint function"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def about_tr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🐬 DOLPHIN Hakkında\n\n"
        "DOLPHIN, Base Mainnet üzerinde oluşturulmuş topluluk odaklı bir ERC-20 token projesidir.\n\n"
        "Zora veya hazır token oluşturucu platformlar kullanılmadan, özel akıllı kontrat ile doğrudan deploy edilmiştir.\n\n"
        "Temel şeffaflık noktaları:\n"
        "✅ Doğrulanmış kontratlar\n"
        "✅ 200M kilitli vesting\n"
        "✅ LP'nin %100'ü 13 Haziran 2028'e kadar kilitli\n"
        "✅ Safe Multisig yönetimi\n"
        "✅ Sabit arz\n"
        "✅ Mint fonksiyonu yok"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if update.effective_message and chat:
        await update.effective_message.reply_text(
            f"Chat ID:\n{chat.id}\n\nChat Title:\n{chat.title or 'Private Chat'}"
        )


async def moderation_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Safety switch: moderation is disabled by default so the bot will not delete
    # normal group messages unless MODERATION_ENABLED=true is explicitly set.
    if not MODERATION_ENABLED:
        return

    msg = update.effective_message

    if not msg or not msg.text:
        return

    if await is_user_admin(update, context):
        return

    delete_reason = None
    warning_enabled = False
    warning_text = ""

    if contains_bad_word(msg.text):
        delete_reason = "bad_word"
        warning_enabled = BAD_WORD_WARN
        warning_text = BAD_WORD_WARNING_TEXT
    elif contains_blocked_link(msg.text):
        delete_reason = "link"
        warning_enabled = LINK_WARN
        warning_text = LINK_WARNING_TEXT

    if not delete_reason:
        return

    chat = update.effective_chat
    user = update.effective_user

    try:
        await msg.delete()
        logger.info(
            "Filtered message deleted | reason=%s | chat=%s | user=%s",
            delete_reason,
            chat.id if chat else "n/a",
            user.id if user else "n/a",
        )
    except Exception as e:
        logger.warning("Filtered message could not be deleted: %s", e)

    if warning_enabled and chat:
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=warning_text,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning("Warning message could not be sent: %s", e)

    raise ApplicationHandlerStop


async def ca_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "🐬 DOLPHIN Contract Address\n\n"
            f"`{TOKEN_ADDRESS}`\n\n"
            "🌊 Network: Base Mainnet",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


async def ca_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.strip().lower()

    ca_triggers = {
        "ca",
        "contract",
        "contract address",
        "kontrat",
        "kontrat adresi",
    }

    if text not in ca_triggers:
        return

    await ca_command(update, context)


async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.new_chat_members:
        return

    if is_tr_chat(update):
        text = welcome_text_tr()
    elif is_global_chat(update):
        text = welcome_text_en()
    else:
        text = welcome_text_bilingual()

    await msg.reply_text(text, disable_web_page_preview=True)


async def channel_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.strip().lower()

    command_map = {
        "/risktr": risk_tr_command,
        "/vestingtr": vesting_tr_command,
        "/lockedtr": locked_tr_command,
        "/supplytr": supply_tr_command,
        "/tokenomicstr": tokenomics_tr_command,
        "/contractstr": contracts_tr_command,
        "/safetr": safe_tr_command,
        "/ownertr": owner_tr_command,
        "/verifytr": verify_tr_command,
        "/linkstr": links_tr_command,
        "/abouttr": about_tr_command,
        "/helptr": help_tr_command,
        "/risk": risk_command,
        "/vesting": vesting_command,
        "/locked": locked_command,
        "/supply": supply_command,
        "/tokenomics": tokenomics_command,
        "/contracts": contracts_command,
        "/safe": safe_command,
        "/owner": owner_command,
        "/verify": verify_command,
        "/links": links_command,
        "/about": about_command,
        "/ca": ca_command,
        "/contract": ca_command,
        "/kontrat": ca_command,
        "/help": help_command,
    }

    for command, handler in command_map.items():
        if text.startswith(command):
            await handler(update, context)
            return


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN boş. .env içine BOT_TOKEN girmelisin.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))

    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("helptr", help_tr_command))

    app.add_handler(CommandHandler("risk", risk_command))
    app.add_handler(CommandHandler("risktr", risk_tr_command))

    app.add_handler(CommandHandler("vesting", vesting_command))
    app.add_handler(CommandHandler("vestingtr", vesting_tr_command))

    app.add_handler(CommandHandler("locked", locked_command))
    app.add_handler(CommandHandler("lockedtr", locked_tr_command))

    app.add_handler(CommandHandler("supply", supply_command))
    app.add_handler(CommandHandler("supplytr", supply_tr_command))

    app.add_handler(CommandHandler("tokenomics", tokenomics_command))
    app.add_handler(CommandHandler("tokenomicstr", tokenomics_tr_command))

    app.add_handler(CommandHandler("contracts", contracts_command))
    app.add_handler(CommandHandler("contractstr", contracts_tr_command))

    app.add_handler(CommandHandler("safe", safe_command))
    app.add_handler(CommandHandler("safetr", safe_tr_command))

    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CommandHandler("ownertr", owner_tr_command))

    app.add_handler(CommandHandler("verify", verify_command))
    app.add_handler(CommandHandler("verifytr", verify_tr_command))

    app.add_handler(CommandHandler("links", links_command))
    app.add_handler(CommandHandler("linkstr", links_tr_command))

    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("abouttr", about_tr_command))

    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CommandHandler("ca", ca_command))
    app.add_handler(CommandHandler("contract", ca_command))
    app.add_handler(CommandHandler("kontrat", ca_command))

    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            moderation_message,
        ),
        group=-1,
    )

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome_new_members,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL & filters.TEXT,
            channel_command_message,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ca_text_message,
        )
    )

    logger.info("DOLPHIN Transparency Bot başladı.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
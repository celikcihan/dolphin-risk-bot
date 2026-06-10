#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
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

TOTAL_SUPPLY = os.getenv("TOTAL_SUPPLY", "499999999")
LOCKED_SUPPLY = os.getenv("LOCKED_SUPPLY", "200000000")

WEBSITE = os.getenv("WEBSITE", "https://dolphin-trust-dao.lovable.app/")
TELEGRAM = os.getenv("TELEGRAM", "https://t.me/DolphinTokenTurkiye")
X_LINK = os.getenv("X", "")

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

async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if update.effective_message and chat:
        await update.effective_message.reply_text(
            f"Chat ID:\n{chat.id}\n\nChat Title:\n{chat.title or 'Private Chat'}"
        )

def short_addr(addr: str) -> str:
    if not addr or len(addr) < 12:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def main_menu_text() -> str:
    return (
        "🐬 DOLPHIN Transparency Bot\n\n"
        "Available commands:\n"
        "/risk - Project risk report\n"
        "/vesting - Locked vesting details\n"
        "/locked - Locked token information\n"
        "/supply - Total token supply\n"
        "/tokenomics - Token distribution\n"
        "/contracts - Contract addresses\n"
        "/safe - Safe multisig information\n"
        "/owner - Contract owner information\n"
        "/verify - Contract verification status\n"
        "/links - Official links\n"
        "/about - About DOLPHIN\n"
        "/help - Show all commands"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            main_menu_text(),
            disable_web_page_preview=True,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            main_menu_text(),
            disable_web_page_preview=True,
        )


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
        "✅ Trading currently disabled\n"
        "✅ Liquidity not opened yet\n\n"
        "🔒 Locked Vesting\n"
        "Amount: 200,000,000 DOLPHIN\n"
        "Cliff: 12 months\n"
        "Vesting: 36 months\n"
        "Current releasable amount: 0 DOLPHIN\n\n"
        "🛡️ Safe Multisig\n"
        f"{SAFE_ADDRESS}\n\n"
        "📜 Token Contract\n"
        f"{TOKEN_ADDRESS}\n\n"
        "Note: LP and trading checks will be added after liquidity is created."
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


async def locked_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔐 Locked Token Status\n\n"
        f"Total Supply: {int(TOTAL_SUPPLY):,} DOLPHIN\n"
        f"Locked Supply: {int(LOCKED_SUPPLY):,} DOLPHIN\n"
        "Locked Share: 40%\n\n"
        "Status:\n"
        "✅ Locked in verified vesting contract\n"
        "✅ Current releasable amount: 0 DOLPHIN\n"
        "✅ Beneficiary: Safe Multisig"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def supply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 DOLPHIN Supply\n\n"
        f"Total Supply: {int(TOTAL_SUPPLY):,} DOLPHIN\n"
        "Mintable: No\n"
        "Burnable: Yes\n\n"
        "The supply is fixed. No additional DOLPHIN can be minted."
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def tokenomics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📊 DOLPHIN Tokenomics\n\n"
        "🔒 Locked Vesting: 200,000,000 (40%)\n"
        "🌊 LP Reserve: 179,999,999 (36%)\n"
        "🤝 Supporters: 45,000,000 (9%)\n"
        "👥 Team: 30,000,000 (6%)\n"
        "📢 Marketing: 20,000,000 (4%)\n"
        "🔥 Burn Reserve: 15,000,000 (3%)\n"
        "💻 Webmaster: 10,000,000 (2%)\n\n"
        "Total Supply: 499,999,999 DOLPHIN"
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
        f"{BASESCAN_SAFE}"
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
    ])

    if update.effective_message:
        await update.effective_message.reply_text(
            "\n".join(lines),
            disable_web_page_preview=True,
        )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🐬 About DOLPHIN\n\n"
        "DOLPHIN is a community-driven ERC-20 token deployed on Base Mainnet.\n\n"
        "It was deployed directly with a custom smart contract, not through Zora or token generator platforms.\n\n"
        "Core transparency points:\n"
        "✅ Verified contracts\n"
        "✅ 200M locked vesting\n"
        "✅ Safe Multisig governance\n"
        "✅ Fixed supply\n"
        "✅ No mint function"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def channel_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.strip().lower()

    command_map = {
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
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("risk", risk_command))
    app.add_handler(CommandHandler("vesting", vesting_command))
    app.add_handler(CommandHandler("locked", locked_command))
    app.add_handler(CommandHandler("supply", supply_command))
    app.add_handler(CommandHandler("tokenomics", tokenomics_command))
    app.add_handler(CommandHandler("contracts", contracts_command))
    app.add_handler(CommandHandler("safe", safe_command))
    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CommandHandler("verify", verify_command))
    app.add_handler(CommandHandler("links", links_command))
    app.add_handler(CommandHandler("about", about_command))

    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL & filters.TEXT,
            channel_command_message,
        )
    )

    logger.info("DOLPHIN Transparency Bot başladı.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
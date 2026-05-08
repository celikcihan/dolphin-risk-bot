#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
from typing import Dict, Any, Optional, Set

import requests


DEX_BASE = "https://api.dexscreener.com"
TG_BASE = "https://api.telegram.org"
ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

CHAIN = os.getenv("CHAIN", "base")
CHAIN_ID = int(os.getenv("CHAIN_ID", "8453"))

TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS", "").lower()
PAIR_ADDRESS = os.getenv("PAIR_ADDRESS", "").lower()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

PROJECT_NAME = os.getenv("PROJECT_NAME", "IRVUS")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "15"))

MIN_BUY_ALERT_USD = float(os.getenv("MIN_BUY_ALERT_USD", "25"))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("irvus-buy-bot")


session = requests.Session()
session.headers.update({
    "User-Agent": "IRVUS-BUY-BOT/1.0"
})


seen_hashes: Set[str] = set()


def fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "n/a"

    if abs(v) >= 1:
        return f"${v:,.2f}"

    return f"${v:.10f}"


def fmt_number(v: Optional[float]) -> str:
    if v is None:
        return "n/a"

    return f"{v:,.2f}"


def get_pair() -> Dict[str, Any]:
    url = f"{DEX_BASE}/latest/dex/pairs/{CHAIN}/{PAIR_ADDRESS}"

    r = session.get(url, timeout=20)
    r.raise_for_status()

    data = r.json()
    pairs = data.get("pairs", [])

    if not pairs:
        raise ValueError("Pair bulunamadı.")

    return pairs[0]


def get_holder_count() -> Optional[int]:
    params = {
        "chainid": CHAIN_ID,
        "module": "token",
        "action": "tokenholdercount",
        "contractaddress": TOKEN_ADDRESS,
        "apikey": ETHERSCAN_API_KEY,
    }

    try:
        r = session.get(
            ETHERSCAN_V2_BASE,
            params=params,
            timeout=20,
        )

        r.raise_for_status()

        data = r.json()

        if str(data.get("status")) == "1":
            return int(data.get("result"))

    except Exception as e:
        logger.warning("Holder count alınamadı: %s", e)

    return None


def get_wallet_token_balance(wallet: str) -> Optional[float]:
    params = {
        "chainid": CHAIN_ID,
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": TOKEN_ADDRESS,
        "address": wallet,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY,
    }

    try:
        r = session.get(
            ETHERSCAN_V2_BASE,
            params=params,
            timeout=20,
        )

        r.raise_for_status()

        data = r.json()

        result = data.get("result")

        if result is None:
            return None

        raw = float(result)

        return raw / (10 ** 18)

    except Exception as e:
        logger.warning("Wallet balance alınamadı: %s", e)

    return None


def buy_level_emoji(usd_amount: float) -> str:
    if usd_amount >= 5000:
        return "🐳🐳🐳"
    if usd_amount >= 2000:
        return "🦈🦈🦈"
    if usd_amount >= 500:
        return "🐬🐬🐬"
    return "🐟🐟🐟"


def send_telegram(text: str) -> None:
    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()


def build_message(
    pair: Dict[str, Any],
    tx: Dict[str, Any],
    holders: Optional[int],
    wallet_balance: Optional[float],
) -> str:

    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}

    base_symbol = base.get("symbol", "TOKEN")
    dex_id = pair.get("dexId", "DEX")

    price_usd = float(pair.get("priceUsd") or 0)

    liquidity = (pair.get("liquidity") or {}).get("usd")
    market_cap = pair.get("marketCap")

    tx_hash = tx.get("txHash", "")

    maker = tx.get("maker", "")

    usd_value = float(tx.get("volumeUsd") or 0)

    token_amount = float(tx.get("baseAmount") or 0)

    quote_amount = float(tx.get("quoteAmount") or 0)

    quote_symbol = quote.get("symbol", "ETH")

    chart_url = pair.get("url", "")

    emoji = buy_level_emoji(usd_value)

    wallet_value = None

    if wallet_balance is not None and price_usd > 0:
        wallet_value = wallet_balance * price_usd

    lines = []

    lines.append(f"🟢 {PROJECT_NAME} BUY!")
    lines.append("")
    lines.append(emoji)
    lines.append("")
    lines.append(
        f"💵 Spent: {quote_amount:.4f} {quote_symbol} ({fmt_money(usd_value)})"
    )
    lines.append(
        f"🪙 Got: {fmt_number(token_amount)} {base_symbol}"
    )
    lines.append("")
    lines.append(f"📈 Buy Price: {fmt_money(price_usd)}")

    if wallet_balance is not None:
        if wallet_value is not None:
            lines.append(
                f"👤 Wallet Holdings: {fmt_number(wallet_balance)} {base_symbol} ({fmt_money(wallet_value)})"
            )
        else:
            lines.append(
                f"👤 Wallet Holdings: {fmt_number(wallet_balance)} {base_symbol}"
            )

    lines.append(f"🏪 DEX: {dex_id}")

    if holders is not None:
        lines.append(f"👥 Holders: {holders:,}")

    if liquidity is not None:
        lines.append(f"💧 Liquidity: {fmt_money(float(liquidity))}")

    if market_cap is not None:
        lines.append(f"🏦 Market Cap: {fmt_money(float(market_cap))}")

    lines.append("")
    lines.append(
        f"🔗 TX: https://basescan.org/tx/{tx_hash}"
    )

    if chart_url:
        lines.append(f"📊 Chart: {chart_url}")

    if maker:
        lines.append("")
        lines.append(
            f"👛 Wallet: {maker[:6]}...{maker[-4:]}"
        )

    return "\n".join(lines)


def fetch_latest_buys(pair: Dict[str, Any]) -> list[Dict[str, Any]]:
    txns = pair.get("txns") or {}

    latest = txns.get("latest") or []

    buys = []

    for tx in latest:
        tx_type = str(tx.get("txType", "")).lower()

        if tx_type != "buy":
            continue

        usd_value = float(tx.get("volumeUsd") or 0)

        if usd_value < MIN_BUY_ALERT_USD:
            continue

        buys.append(tx)

    return buys


def main() -> None:
    logger.info("IRVUS BUY BOT başladı.")

    while True:
        try:
            pair = get_pair()

            holders = get_holder_count()

            buys = fetch_latest_buys(pair)

            for tx in buys:
                tx_hash = tx.get("txHash")

                if not tx_hash:
                    continue

                if tx_hash in seen_hashes:
                    continue

                seen_hashes.add(tx_hash)

                maker = tx.get("maker", "")

                wallet_balance = None

                if maker:
                    wallet_balance = get_wallet_token_balance(maker)

                msg = build_message(
                    pair=pair,
                    tx=tx,
                    holders=holders,
                    wallet_balance=wallet_balance,
                )

                send_telegram(msg)

                logger.info("BUY alert gönderildi: %s", tx_hash)

            if len(seen_hashes) > 5000:
                seen_hashes.clear()

        except Exception as e:
            logger.exception("BUY BOT hata verdi: %s", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
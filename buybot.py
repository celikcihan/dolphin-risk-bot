#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
from typing import Any, Dict, List, Optional, Set

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

TOKEN_DECIMALS = int(os.getenv("TOKEN_DECIMALS", "18"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("irvus-buy-bot")

session = requests.Session()
session.headers.update({"User-Agent": "IRVUS-BUY-BOT/2.0"})

seen_hashes: Set[str] = set()
first_run = True
cached_pair: Optional[Dict[str, Any]] = None


def fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1:
        return f"${v:,.2f}"
    return f"${v:.10f}"


def fmt_number(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1_000_000:
        return f"{v:,.0f}"
    if abs(v) >= 1_000:
        return f"{v:,.2f}"
    return f"{v:,.6f}"


def short_wallet(addr: str) -> str:
    if not addr:
        return "n/a"
    return f"{addr[:6]}...{addr[-4:]}"


def send_telegram(text: str) -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN boş.")
    if not CHANNEL_ID:
        raise ValueError("CHANNEL_ID boş.")

    url = f"{TG_BASE}/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    r = session.post(url, json=payload, timeout=20)
    r.raise_for_status()


def get_token_pairs() -> List[Dict[str, Any]]:
    url = f"{DEX_BASE}/token-pairs/v1/{CHAIN}/{TOKEN_ADDRESS}"

    r = session.get(url, timeout=20)
    r.raise_for_status()

    data = r.json()

    if isinstance(data, list):
        return data

    return data.get("pairs", []) or []


def get_pair_by_address(pair_address: str) -> Optional[Dict[str, Any]]:
    url = f"{DEX_BASE}/latest/dex/pairs/{CHAIN}/{pair_address}"

    r = session.get(url, timeout=20)
    r.raise_for_status()

    data = r.json()
    pairs = data.get("pairs") or []

    if not pairs:
        return None

    return pairs[0]


def choose_best_pair(pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not pairs:
        raise ValueError("Token için DexScreener pair bulunamadı.")

    def score(p: Dict[str, Any]) -> float:
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        vol = float((p.get("volume") or {}).get("h24") or 0)
        return liq * 1000 + vol

    return sorted(pairs, key=score, reverse=True)[0]


def get_pair() -> Dict[str, Any]:
    global cached_pair

    if cached_pair:
        return cached_pair

    if PAIR_ADDRESS:
        pair = get_pair_by_address(PAIR_ADDRESS)
        if pair:
            cached_pair = pair
            logger.info("Pair env ile bulundu: %s", PAIR_ADDRESS)
            return pair

        logger.warning("PAIR_ADDRESS ile pair bulunamadı, token üzerinden aranacak.")

    pairs = get_token_pairs()
    pair = choose_best_pair(pairs)

    cached_pair = pair

    logger.info(
        "Otomatik pair seçildi: %s | dex=%s | liquidity=%s",
        pair.get("pairAddress"),
        pair.get("dexId"),
        (pair.get("liquidity") or {}).get("usd"),
    )

    return pair


def refresh_pair(pair_address: str) -> Dict[str, Any]:
    pair = get_pair_by_address(pair_address)
    if not pair:
        raise ValueError("Pair refresh edilemedi.")
    return pair


def get_holder_count() -> Optional[int]:
    params = {
        "chainid": CHAIN_ID,
        "module": "token",
        "action": "tokenholdercount",
        "contractaddress": TOKEN_ADDRESS,
        "apikey": ETHERSCAN_API_KEY,
    }

    try:
        r = session.get(ETHERSCAN_V2_BASE, params=params, timeout=20)
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
        r = session.get(ETHERSCAN_V2_BASE, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        result = data.get("result")

        if result is None:
            return None

        raw = float(result)

        return raw / (10 ** TOKEN_DECIMALS)

    except Exception as e:
        logger.warning("Wallet balance alınamadı: %s", e)

    return None


def get_latest_token_transfers(limit: int = 20) -> List[Dict[str, Any]]:
    params = {
        "chainid": CHAIN_ID,
        "module": "account",
        "action": "tokentx",
        "contractaddress": TOKEN_ADDRESS,
        "page": 1,
        "offset": limit,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY,
    }

    r = session.get(ETHERSCAN_V2_BASE, params=params, timeout=20)
    r.raise_for_status()

    data = r.json()

    result = data.get("result")

    if not isinstance(result, list):
        logger.warning("tokentx beklenen liste dönmedi: %s", data)
        return []

    return result


def is_buy_transfer(tx: Dict[str, Any], pair_address: str) -> bool:
    from_addr = str(tx.get("from", "")).lower()
    to_addr = str(tx.get("to", "")).lower()

    if from_addr != pair_address.lower():
        return False

    if not to_addr:
        return False

    if to_addr in {
        "0x0000000000000000000000000000000000000000",
        "0x000000000000000000000000000000000000dead",
    }:
        return False

    return True


def token_amount_from_transfer(tx: Dict[str, Any]) -> float:
    raw_value = float(tx.get("value") or 0)

    decimals = tx.get("tokenDecimal")

    try:
        decimals_int = int(decimals)
    except Exception:
        decimals_int = TOKEN_DECIMALS

    return raw_value / (10 ** decimals_int)


def build_message(
    pair: Dict[str, Any],
    tx: Dict[str, Any],
    holders: Optional[int],
    wallet_balance: Optional[float],
) -> str:
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}

    base_symbol = base.get("symbol", PROJECT_NAME)
    quote_symbol = quote.get("symbol", "QUOTE")

    dex_id = pair.get("dexId", "DEX")
    chart_url = pair.get("url", "")

    price_usd = float(pair.get("priceUsd") or 0)
    price_native = float(pair.get("priceNative") or 0)

    liquidity_usd = (pair.get("liquidity") or {}).get("usd")
    market_cap = pair.get("marketCap")
    fdv = pair.get("fdv")

    tx_hash = tx.get("hash", "")
    buyer = tx.get("to", "")

    token_amount = token_amount_from_transfer(tx)

    usd_value = token_amount * price_usd if price_usd > 0 else None
    quote_amount = token_amount * price_native if price_native > 0 else None

    wallet_value = None
    if wallet_balance is not None and price_usd > 0:
        wallet_value = wallet_balance * price_usd

    lines: List[str] = []

    lines.append(f"🟢 {PROJECT_NAME} BUY!")
    lines.append("")
    lines.append("✅ New Buy Detected")
    lines.append("")
    
    if quote_amount is not None:
        lines.append(
            f"💵 Spent: {quote_amount:,.6f} {quote_symbol} ({fmt_money(usd_value)})"
        )
    else:
        lines.append(f"💵 Spent: {fmt_money(usd_value)}")

    lines.append(f"🪙 Got: {fmt_number(token_amount)} {base_symbol}")
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

    if liquidity_usd is not None:
        lines.append(f"💧 Liquidity: {fmt_money(float(liquidity_usd))}")

    if market_cap is not None:
        lines.append(f"🏦 Market Cap: {fmt_money(float(market_cap))}")
    elif fdv is not None:
        lines.append(f"📊 FDV: {fmt_money(float(fdv))}")

    lines.append("")
    lines.append(f"👛 Buyer: {short_wallet(buyer)}")
    lines.append(f"🔗 TX: https://basescan.org/tx/{tx_hash}")

    if chart_url:
        lines.append(f"📊 Chart: {chart_url}")

    return "\n".join(lines)


def main() -> None:
    global first_run

    logger.info("IRVUS BUY BOT başladı.")

    if not TOKEN_ADDRESS:
        raise ValueError("TOKEN_ADDRESS boş.")
    if not ETHERSCAN_API_KEY:
        raise ValueError("ETHERSCAN_API_KEY boş.")

    pair = get_pair()
    pair_address = str(pair.get("pairAddress") or "").lower()

    if not pair_address:
        raise ValueError("Pair address alınamadı.")

    logger.info("İzlenen pair: %s", pair_address)

    while True:
        try:
            pair = refresh_pair(pair_address)

            transfers = get_latest_token_transfers(limit=30)

            buy_transfers = [
                tx for tx in transfers
                if is_buy_transfer(tx, pair_address)
            ]

            buy_transfers = list(reversed(buy_transfers))

            holders = get_holder_count()

            for tx in buy_transfers:
                tx_hash = tx.get("hash")

                if not tx_hash:
                    continue

                if tx_hash in seen_hashes:
                    continue

                seen_hashes.add(tx_hash)

                if first_run:
                    continue

                buyer = tx.get("to", "")
                token_amount = token_amount_from_transfer(tx)
                price_usd = float(pair.get("priceUsd") or 0)
                usd_value = token_amount * price_usd

                if usd_value < MIN_BUY_ALERT_USD:
                    logger.info(
                        "Buy küçük olduğu için geçildi: %s | %s",
                        fmt_money(usd_value),
                        tx_hash,
                    )
                    continue

                wallet_balance = None
                if buyer:
                    wallet_balance = get_wallet_token_balance(buyer)

                msg = build_message(
                    pair=pair,
                    tx=tx,
                    holders=holders,
                    wallet_balance=wallet_balance,
                )

                send_telegram(msg)

                logger.info("BUY alert gönderildi: %s", tx_hash)

            first_run = False

            if len(seen_hashes) > 5000:
                seen_hashes.clear()

        except Exception as e:
            logger.exception("BUY BOT hata verdi: %s", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

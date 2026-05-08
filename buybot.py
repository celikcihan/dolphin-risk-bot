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

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

PROJECT_NAME = os.getenv("PROJECT_NAME", "IRVUS")

CHAIN = os.getenv("CHAIN", "base")
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")

TOKEN_ADDRESS = os.getenv("TOKEN_ADDRESS", "").lower()
PAIR_ADDRESS = os.getenv("PAIR_ADDRESS", "").lower()

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "15"))
MIN_BUY_ALERT_USD = float(os.getenv("MIN_BUY_ALERT_USD", "25"))
TOKEN_DECIMALS = int(os.getenv("TOKEN_DECIMALS", "18"))

BLOCK_LOOKBACK = int(os.getenv("BLOCK_LOOKBACK", "30"))

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("irvus-buybot-rpc")

session = requests.Session()
session.headers.update({"User-Agent": "IRVUS-BUYBOT-RPC/1.0"})

seen_hashes: Set[str] = set()
cached_pair: Optional[Dict[str, Any]] = None
last_checked_block: Optional[int] = None


def rpc_call(method: str, params: list[Any]) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params,
    }

    r = session.post(BASE_RPC_URL, json=payload, timeout=30)
    r.raise_for_status()

    data = r.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data.get("result")


def hex_to_int(value: str) -> int:
    return int(value, 16)


def int_to_hex(value: int) -> str:
    return hex(value)


def normalize_topic_address(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def address_to_topic(address: str) -> str:
    clean = address.lower().replace("0x", "")
    return "0x" + clean.rjust(64, "0")


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


def get_latest_block() -> int:
    result = rpc_call("eth_blockNumber", [])
    return hex_to_int(result)


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
        logger.warning("Pair refresh edilemedi, cached pair kullanılacak.")
        return cached_pair or get_pair()
    return pair


def get_transfer_logs(from_block: int, to_block: int, pair_address: str) -> List[Dict[str, Any]]:
    params = {
        "fromBlock": int_to_hex(from_block),
        "toBlock": int_to_hex(to_block),
        "address": TOKEN_ADDRESS,
        "topics": [
            TRANSFER_TOPIC,
            address_to_topic(pair_address),
        ],
    }

    result = rpc_call("eth_getLogs", [params])

    if not isinstance(result, list):
        return []

    return result


def decode_transfer_log(log: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    topics = log.get("topics") or []

    if len(topics) < 3:
        return None

    from_addr = normalize_topic_address(topics[1])
    to_addr = normalize_topic_address(topics[2])

    raw_value_hex = log.get("data", "0x0")
    raw_value = hex_to_int(raw_value_hex)

    token_amount = raw_value / (10 ** TOKEN_DECIMALS)

    tx_hash = log.get("transactionHash", "")

    return {
        "tx_hash": tx_hash,
        "from": from_addr,
        "to": to_addr,
        "token_amount": token_amount,
        "block_number": hex_to_int(log.get("blockNumber", "0x0")),
    }


def get_wallet_token_balance(wallet: str) -> Optional[float]:
    selector = "0x70a08231"
    wallet_clean = wallet.lower().replace("0x", "").rjust(64, "0")
    data = selector + wallet_clean

    call_obj = {
        "to": TOKEN_ADDRESS,
        "data": data,
    }

    try:
        result = rpc_call("eth_call", [call_obj, "latest"])
        raw = hex_to_int(result)
        return raw / (10 ** TOKEN_DECIMALS)
    except Exception as e:
        logger.warning("Wallet balance alınamadı: %s", e)
        return None


def get_holder_count_safe() -> Optional[int]:
    return None


def build_message(
    pair: Dict[str, Any],
    transfer: Dict[str, Any],
    holders: Optional[int],
    wallet_balance: Optional[float],
) -> str:
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}

    base_symbol = base.get("symbol", PROJECT_NAME)
    quote_symbol = quote.get("symbol", "ETH")

    dex_id = pair.get("dexId", "DEX")
    chart_url = pair.get("url", "")

    price_usd = float(pair.get("priceUsd") or 0)
    price_native = float(pair.get("priceNative") or 0)

    liquidity_usd = (pair.get("liquidity") or {}).get("usd")
    market_cap = pair.get("marketCap")
    fdv = pair.get("fdv")

    tx_hash = transfer.get("tx_hash", "")
    buyer = transfer.get("to", "")
    token_amount = float(transfer.get("token_amount") or 0)

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
    else:
        lines.append("👥 Holders: n/a")

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
    global last_checked_block, cached_pair

    logger.info("IRVUS BUY BOT RPC başladı.")

    if not TOKEN_ADDRESS:
        raise ValueError("TOKEN_ADDRESS boş.")
    if not BASE_RPC_URL:
        raise ValueError("BASE_RPC_URL boş.")

    pair = get_pair()
    pair_address = str(pair.get("pairAddress") or "").lower()

    if not pair_address:
        raise ValueError("Pair address alınamadı.")

    logger.info("İzlenen pair: %s", pair_address)

    latest_block = get_latest_block()
    last_checked_block = max(latest_block - BLOCK_LOOKBACK, 0)

    logger.info("Başlangıç block: %s", last_checked_block)

    while True:
        try:
            latest_block = get_latest_block()

            from_block = (last_checked_block or latest_block) + 1
            to_block = latest_block

            if from_block > to_block:
                time.sleep(CHECK_INTERVAL)
                continue

            pair = refresh_pair(pair_address)
            cached_pair = pair

            logs = get_transfer_logs(
                from_block=from_block,
                to_block=to_block,
                pair_address=pair_address,
            )

            holders = get_holder_count_safe()

            for log in logs:
                transfer = decode_transfer_log(log)

                if not transfer:
                    continue

                tx_hash = transfer["tx_hash"]

                if not tx_hash or tx_hash in seen_hashes:
                    continue

                seen_hashes.add(tx_hash)

                token_amount = float(transfer.get("token_amount") or 0)
                price_usd = float(pair.get("priceUsd") or 0)
                usd_value = token_amount * price_usd

                if usd_value < MIN_BUY_ALERT_USD:
                    logger.info(
                        "Buy küçük olduğu için geçildi: %s | %s",
                        fmt_money(usd_value),
                        tx_hash,
                    )
                    continue

                buyer = transfer.get("to", "")
                wallet_balance = get_wallet_token_balance(buyer) if buyer else None

                msg = build_message(
                    pair=pair,
                    transfer=transfer,
                    holders=holders,
                    wallet_balance=wallet_balance,
                )

                send_telegram(msg)

                logger.info("BUY alert gönderildi: %s", tx_hash)

            last_checked_block = to_block

            if len(seen_hashes) > 5000:
                seen_hashes.clear()

        except Exception as e:
            logger.exception("BUY BOT hata verdi: %s", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

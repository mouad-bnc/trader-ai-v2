from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

BINANCE_BASE = "https://api.binance.com"
CONFIG_PATH = Path(__file__).with_name("config.json")
JOURNAL_PATH = Path(__file__).with_name("journal_trades.csv")


@dataclass
class Signal:
    symbol: str
    price: float
    change_24h: float
    rsi: float
    sma20: float
    sma50: float
    score: int
    decision: str
    risk: str
    buy_zone: str
    stop_zone: str
    comment: str


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "base_currency": "USDT",
        "watchlist": ["BTCUSDT", "SOLUSDT", "SUIUSDT", "DOGEUSDT"],
        "risk_profile": "Prudent",
        "max_allocation_per_signal_usdt": 100,
    }


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_ticker(symbol: str) -> dict:
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
    response = requests.get(url, params={"symbol": symbol.upper()}, timeout=12)
    response.raise_for_status()
    return response.json()


def fetch_klines(symbol: str, interval: str = "1d", limit: int = 90) -> pd.DataFrame:
    url = f"{BINANCE_BASE}/api/v3/klines"
    response = requests.get(url, params={"symbol": symbol.upper(), "interval": interval, "limit": limit}, timeout=12)
    response.raise_for_status()
    rows = response.json()
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    return df[["date", "open", "high", "low", "close", "volume"]]


def compute_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, math.nan)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    return float(value) if pd.notna(value) else 50.0


def analyze_symbol(symbol: str, allocation_usdt: float = 100.0) -> Signal:
    ticker = fetch_ticker(symbol)
    df = fetch_klines(symbol)
    price = float(ticker["lastPrice"])
    change = float(ticker["priceChangePercent"])
    close = df["close"]
    rsi = compute_rsi(close)
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])

    score = 50
    reasons: List[str] = []

    if price > sma20:
        score += 10
        reasons.append("prix au-dessus de la moyenne 20j")
    else:
        score -= 5
        reasons.append("prix sous la moyenne 20j")

    if sma20 > sma50:
        score += 15
        reasons.append("tendance moyenne positive")
    else:
        score -= 10
        reasons.append("tendance moyenne fragile")

    if 35 <= rsi <= 55:
        score += 15
        reasons.append("RSI équilibré")
    elif rsi < 35:
        score += 20
        reasons.append("RSI bas, potentiel rebond")
    elif rsi > 70:
        score -= 20
        reasons.append("RSI élevé, risque de surchauffe")
    else:
        score += 2
        reasons.append("RSI acceptable")

    if change < -6:
        score -= 10
        reasons.append("chute 24h forte")
    elif -6 <= change <= 3:
        score += 8
        reasons.append("variation 24h raisonnable")
    else:
        score -= 5
        reasons.append("hausse 24h déjà avancée")

    score = max(0, min(100, int(score)))

    if score >= 75:
        decision = f"Renforcer léger, max {allocation_usdt:.0f} USDT"
        risk = "Moyen"
    elif score >= 60:
        decision = "Surveiller / entrée partielle possible"
        risk = "Moyen"
    elif score >= 45:
        decision = "Attendre"
        risk = "Modéré"
    else:
        decision = "Ne rien faire"
        risk = "Élevé"

    buy_low = price * 0.97
    buy_high = price * 1.01
    stop = price * 0.92
    return Signal(
        symbol=symbol.upper(),
        price=price,
        change_24h=change,
        rsi=rsi,
        sma20=sma20,
        sma50=sma50,
        score=score,
        decision=decision,
        risk=risk,
        buy_zone=f"{buy_low:.4g} - {buy_high:.4g}",
        stop_zone=f"≈ {stop:.4g}",
        comment=", ".join(reasons),
    )


def analyze_watchlist(symbols: List[str], allocation_usdt: float = 100.0) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        try:
            s = analyze_symbol(symbol, allocation_usdt)
            rows.append(s.__dict__)
            time.sleep(0.15)
        except Exception as exc:
            rows.append({
                "symbol": symbol.upper(), "price": None, "change_24h": None, "rsi": None,
                "sma20": None, "sma50": None, "score": 0, "decision": "Erreur données",
                "risk": "N/A", "buy_zone": "N/A", "stop_zone": "N/A", "comment": str(exc)
            })
    return pd.DataFrame(rows)


def ensure_journal() -> None:
    if not JOURNAL_PATH.exists():
        pd.DataFrame(columns=["date", "symbol", "action", "amount_usdt", "price", "notes"]).to_csv(JOURNAL_PATH, index=False)


def load_journal() -> pd.DataFrame:
    ensure_journal()
    return pd.read_csv(JOURNAL_PATH)


def add_journal_entry(symbol: str, action: str, amount_usdt: float, price: float, notes: str) -> None:
    ensure_journal()
    df = load_journal()
    entry = {
        "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol.upper(),
        "action": action,
        "amount_usdt": amount_usdt,
        "price": price,
        "notes": notes,
    }
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(JOURNAL_PATH, index=False)

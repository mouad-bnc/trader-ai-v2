import requests
from statistics import mean

BASE_URL = "https://api.binance.com"


def get_24h(symbol: str) -> dict:
    url = f"{BASE_URL}/api/v3/ticker/24hr"
    r = requests.get(url, params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return r.json()


def get_klines(symbol: str, interval: str = "1d", limit: int = 30) -> list:
    url = f"{BASE_URL}/api/v3/klines"
    r = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()


def sma(values, period):
    if len(values) < period:
        return None
    return mean(values[-period:])


def analyze_symbol(symbol: str) -> dict:
    data = get_24h(symbol)
    klines = get_klines(symbol)

    price = float(data["lastPrice"])
    change_24h = float(data["priceChangePercent"])
    volume = float(data["quoteVolume"])
    closes = [float(k[4]) for k in klines]

    sma7 = sma(closes, 7)
    sma20 = sma(closes, 20)

    score = 50

    if change_24h <= -5:
        score += 15
    elif change_24h <= -2:
        score += 8
    elif change_24h >= 8:
        score -= 15
    elif change_24h >= 4:
        score -= 8

    if sma7 and sma20:
        if sma7 > sma20:
            score += 10
        else:
            score -= 5

    if volume > 100_000_000:
        score += 5

    score = max(0, min(100, round(score)))

    if score >= 70:
        decision = "Renforcer léger"
        action = "Opportunité intéressante, mais garder une allocation prudente."
    elif score >= 55:
        decision = "Attendre / surveiller"
        action = "Zone neutre. Attendre une meilleure entrée ou confirmation."
    else:
        decision = "Ne rien faire"
        action = "Risque trop élevé ou momentum défavorable."

    buy_zone_low = price * 0.96
    buy_zone_high = price * 0.99
    stop_level = price * 0.90

    return {
        "symbol": symbol,
        "price": price,
        "change_24h": change_24h,
        "volume": volume,
        "sma7": sma7,
        "sma20": sma20,
        "score": score,
        "decision": decision,
        "action": action,
        "buy_zone_low": buy_zone_low,
        "buy_zone_high": buy_zone_high,
        "stop_level": stop_level,
    }

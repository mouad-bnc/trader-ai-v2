import json
from datetime import datetime

import streamlit as st

from trader_core import analyze_symbol

st.set_page_config(
    page_title="Trader AI V3",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Trader AI V3")
st.caption("Assistant crypto personnel — analyse uniquement, aucun ordre Binance n’est exécuté.")

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception:
    config = {"watchlist": ["BTCUSDT", "SOLUSDT", "SUIUSDT", "DOGEUSDT"], "capital_to_add_usdt": 100}

with st.sidebar:
    st.header("⚙️ Paramètres")
    watchlist_text = st.text_area(
        "Watchlist",
        value=", ".join(config.get("watchlist", [])),
        help="Exemple : BTCUSDT, SOLUSDT, SUIUSDT, DOGEUSDT",
    )
    capital = st.number_input("Renfort prévu (USDT)", min_value=10, max_value=10000, value=int(config.get("capital_to_add_usdt", 100)))
    refresh = st.button("🔄 Actualiser")

symbols = [s.strip().upper() for s in watchlist_text.split(",") if s.strip()]

st.subheader("🧭 Décision rapide")
st.write(f"Dernière mise à jour : **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")

if not symbols:
    st.warning("Ajoute au moins une paire, par exemple BTCUSDT.")
    st.stop()

results = []
for symbol in symbols:
    try:
        results.append(analyze_symbol(symbol))
    except Exception as e:
        st.error(f"Erreur sur {symbol}: {e}")

if not results:
    st.stop()

best = max(results, key=lambda x: x["score"])

col1, col2, col3 = st.columns(3)
col1.metric("Meilleure opportunité", best["symbol"])
col2.metric("Score", f"{best['score']}/100")
col3.metric("Action", best["decision"])

if best["score"] >= 70:
    st.success(f"Renfort possible : commencer prudemment, par exemple **{capital * 0.30:.0f} à {capital * 0.50:.0f} USDT** sur {best['symbol']}.")
elif best["score"] >= 55:
    st.info("Marché neutre : surveiller, ne pas forcer l’entrée.")
else:
    st.warning("Aucune opportunité forte pour le moment.")

st.divider()

for r in results:
    st.markdown(f"### {r['symbol']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prix", f"{r['price']:.6f}")
    c2.metric("24h", f"{r['change_24h']:.2f}%")
    c3.metric("Score", f"{r['score']}/100")
    c4.metric("Décision", r["decision"])

    st.write(r["action"])
    st.write(f"Zone d’achat indicative : **{r['buy_zone_low']:.6f} → {r['buy_zone_high']:.6f}**")
    st.write(f"Stop indicatif : **{r['stop_level']:.6f}**")
    st.caption("Rappel : ceci n’est pas un conseil financier. Utilise une taille de position prudente.")
    st.divider()

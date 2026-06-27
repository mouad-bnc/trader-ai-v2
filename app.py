from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from trader_core import (
    add_journal_entry,
    analyze_watchlist,
    fetch_klines,
    load_config,
    load_journal,
    save_config,
)

st.set_page_config(page_title="Trader AI v2", page_icon="📈", layout="wide")

st.title("📈 Trader AI v2")
st.caption("Assistant crypto personnel. Lecture seule. Aucun ordre Binance n'est exécuté.")

config = load_config()

with st.sidebar:
    st.header("Réglages")
    default_symbols = ", ".join(config.get("watchlist", ["BTCUSDT", "SOLUSDT", "SUIUSDT", "DOGEUSDT"]))
    symbols_text = st.text_area("Watchlist Binance", default_symbols, help="Exemple: BTCUSDT, SOLUSDT, SUIUSDT, DOGEUSDT")
    allocation = st.number_input("Montant max par signal (USDT)", min_value=10, max_value=10000, value=int(config.get("max_allocation_per_signal_usdt", 100)), step=10)
    risk_profile = st.selectbox("Profil", ["Prudent", "Équilibré", "Dynamique"], index=["Prudent", "Équilibré", "Dynamique"].index(config.get("risk_profile", "Prudent")))
    if st.button("Sauvegarder"):
        symbols = [s.strip().upper() for s in symbols_text.replace("\n", ",").split(",") if s.strip()]
        config.update({"watchlist": symbols, "max_allocation_per_signal_usdt": allocation, "risk_profile": risk_profile})
        save_config(config)
        st.success("Réglages sauvegardés")

symbols = [s.strip().upper() for s in symbols_text.replace("\n", ",").split(",") if s.strip()]

col1, col2, col3 = st.columns(3)
col1.metric("Cryptos suivies", len(symbols))
col2.metric("Profil", risk_profile)
col3.metric("Renfort max", f"{allocation:.0f} USDT")

st.subheader("Analyse du marché")
with st.spinner("Analyse en cours..."):
    df = analyze_watchlist(symbols, allocation)

show = df[["symbol", "price", "change_24h", "rsi", "score", "decision", "risk", "buy_zone", "stop_zone", "comment"]].copy()
show.columns = ["Crypto", "Prix", "24h %", "RSI", "Score", "Décision", "Risque", "Zone achat", "Stop indicatif", "Pourquoi"]
st.dataframe(show, use_container_width=True, hide_index=True)

best = df.sort_values("score", ascending=False).iloc[0]
st.info(f"Meilleure opportunité actuelle selon le score: {best['symbol']} avec {int(best['score'])}/100. Décision: {best['decision']}.")

st.subheader("Graphique")
selected = st.selectbox("Choisir une crypto", symbols)
try:
    k = fetch_klines(selected, limit=120)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=k["date"], open=k["open"], high=k["high"], low=k["low"], close=k["close"], name=selected))
    fig.update_layout(height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
except Exception as exc:
    st.warning(f"Graphique indisponible: {exc}")

st.subheader("Journal de trading")
with st.form("journal"):
    j1, j2, j3, j4 = st.columns(4)
    jsymbol = j1.selectbox("Crypto", symbols, key="journal_symbol")
    action = j2.selectbox("Action", ["Achat", "Vente", "Observation", "Spot Grid", "Renfort"])
    amount = j3.number_input("Montant USDT", min_value=0.0, value=0.0, step=10.0)
    price = j4.number_input("Prix", min_value=0.0, value=0.0, step=0.0001, format="%.8f")
    notes = st.text_input("Notes")
    submitted = st.form_submit_button("Ajouter au journal")
    if submitted:
        add_journal_entry(jsymbol, action, amount, price, notes)
        st.success("Entrée ajoutée")

journal = load_journal()
st.dataframe(journal.tail(50), use_container_width=True, hide_index=True)

st.warning("Ce tableau n'est pas un conseil financier. Utilise-le comme aide à la décision, jamais comme signal automatique.")

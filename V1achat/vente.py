import streamlit as st
import yfinance as yf
import pandas as pd

st.title("Simulation de marché et trading virtuel")

@st.cache_data
def load_data():
    tickers = {
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "Solana": "SOL-USD",
        "CAC40": "^FCHI",
        "S&P500": "^GSPC",
        "Apple": "AAPL",
        "Google": "GOOGL",
        "LVMH": "MC.PA",
        "Or": "GC=F",
        "Argent": "SI=F"
    }

    data = yf.download(list(tickers.values()), period="5y")["Close"]
    data.columns = tickers.keys()

    # pour remplir les trous
    data = data.ffill()

    # pour les colonnes vides
    data = data.dropna(axis=1, how="all")

    return data

data = load_data()

if "cash" not in st.session_state:
    st.session_state.cash = 10_000

if "positions" not in st.session_state:
    st.session_state.positions = {name: 0 for name in data.columns}

if "history" not in st.session_state:
    st.session_state.history = []


st.write("Aperçu des données :", data.head())

actifs = st.multiselect("Actifs à afficher", data.columns.tolist(), default=["Bitcoin"])
jour = st.slider("Position dans le temps", 0, len(data) - 1, 10)

subset = data.iloc[:jour + 1]
prix_actuels = subset.iloc[-1]

st.subheader("Évolution des prix")
st.line_chart(subset[actifs])

st.subheader("Valeurs actuelles")
st.dataframe(prix_actuels[actifs])






st.header("Trading")

actif = st.selectbox("Sélectionne un actif", data.columns)
quantite = st.number_input("Quantité", min_value=1, value=1)

prix = prix_actuels[actif]

col_achat, col_vente = st.columns(2)

with col_achat:
    if st.button("Acheter"):
        coût = prix * quantite
        if st.session_state.cash >= coût:
            st.session_state.cash -= coût
            st.session_state.positions[actif] += quantite
            st.session_state.history.append(("Achat", actif, quantite, prix))
            st.success(f"Achat de {quantite} {actif} à {prix:.2f}")
        else:
            st.error("Fonds insuffisants.")

with col_vente:
    if st.button("Vendre"):
        if st.session_state.positions[actif] >= quantite:
            st.session_state.positions[actif] -= quantite
            st.session_state.cash += prix * quantite
            st.session_state.history.append(("Vente", actif, quantite, prix))
            st.success(f"Vente de {quantite} {actif} à {prix:.2f}")
        else:
            st.error("Quantité insuffisante pour vendre.")






st.header("Portefeuille")

df_positions = pd.DataFrame({
    "Actif": data.columns,
    "Quantité": [st.session_state.positions[a] for a in data.columns],
    "Prix actuel": [prix_actuels[a] for a in data.columns]
})

df_positions["Valeur"] = df_positions["Quantité"] * df_positions["Prix actuel"]

st.subheader("Positions détenues")
st.dataframe(df_positions)

valeur_positions = df_positions["Valeur"].sum()
valeur_totale = valeur_positions + st.session_state.cash

st.metric("Cash disponible", f"{st.session_state.cash:,.2f} $")
st.metric("Valeur totale du portefeuille", f"{valeur_totale:,.2f} $")

# ---------------------------------------------------------
# Historique des transactions
# ---------------------------------------------------------
st.header("Historique des transactions")

if st.session_state.history:
    hist = pd.DataFrame(st.session_state.history, columns=["Type", "Actif", "Quantité", "Prix"])
    st.dataframe(hist)
else:
    st.write("Aucune transaction pour le moment.")

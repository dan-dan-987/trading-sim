import random
import pandas as pd
import streamlit as st

from db import get_user_data, get_history, calculate_positions, save_transaction
from market import load_market_data
from orders import (
    get_open_orders,
    get_order_history,
    save_order,
    update_order,
    update_order_status,
    check_orders
)


def afficher_arcade_mode(user_id: str):
    st.title("Simulation de marché et trading virtuel")

    market_data = load_market_data()

    if "start_index" not in st.session_state:
        max_start = max(1, len(market_data) - 200)
        st.session_state.start_index = random.randint(0, max_start)

    if "current_index" not in st.session_state:
        st.session_state.current_index = st.session_state.start_index

    st.subheader("Avancer dans le temps")

    nb_jours = st.number_input("Nombre de jours à avancer", min_value=1, max_value=200, value=10)

    if st.button("Avancer"):
        new_index = min(st.session_state.current_index + nb_jours, len(market_data) - 1)
        st.session_state.current_index = new_index

    jour = st.session_state.current_index
    subset = market_data.iloc[st.session_state.start_index:jour + 1]
    prix_actuels = subset.iloc[-1]

    current_cash = get_user_data(user_id)
    history_df = get_history(user_id)
    positions = calculate_positions(history_df, market_data.columns)

    check_orders(user_id, prix_actuels)

    current_cash = get_user_data(user_id)
    history_df = get_history(user_id)
    positions = calculate_positions(history_df, market_data.columns)

    actifs = st.multiselect("Actifs à afficher", market_data.columns.tolist(), default=["Bitcoin"])
    st.line_chart(subset[actifs])

    st.header("Trading manuel")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        actif_sel = st.selectbox("Sélectionne un actif", market_data.columns)
        quantite = st.number_input("Quantité", min_value=1, value=1)

    prix_unitaire = prix_actuels[actif_sel]

    with col_t2:
        st.write(f"Prix actuel : {prix_unitaire:.2f} $")
        st.write(f"Total opération : {(prix_unitaire * quantite):,.2f} $")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("ACHETER", use_container_width=True):
            cout = prix_unitaire * quantite
            if current_cash >= cout:
                save_transaction(user_id, "Achat", actif_sel, quantite, prix_unitaire, current_cash - cout)
                st.success("Achat effectué")
                st.rerun()
            else:
                st.error("Fonds insuffisants.")

    with c2:
        if st.button("VENDRE", use_container_width=True):
            if positions.get(actif_sel, 0) >= quantite:
                gain = prix_unitaire * quantite
                save_transaction(user_id, "Vente", actif_sel, quantite, prix_unitaire, current_cash + gain)
                st.success("Vente effectuée")
                st.rerun()
            else:
                st.error("Pas assez de titres.")

    st.header("Ordres avancés")

    col_o1, col_o2, col_o3, col_o4 = st.columns(4)
    with col_o1:
        type_ordre = st.selectbox("Type d’ordre", ["Limit", "Stop-Loss", "Take-Profit"])
    with col_o2:
        prix_cible = st.number_input("Prix cible", min_value=0.0, value=float(prix_unitaire))
    with col_o3:
        quantite_ordre = st.number_input("Quantité ordre", min_value=1, value=1)
    with col_o4:
        trailing = st.checkbox("Trailing order")

    if st.button("Placer l’ordre avancé"):
        if prix_cible <= 0:
            st.error("Le prix cible doit être supérieur à 0.")
        else:
            save_order(user_id, actif_sel, type_ordre, prix_cible, quantite_ordre, trailing)
            st.success("Ordre avancé placé")

    open_orders = get_open_orders(user_id)

    if open_orders:
        st.subheader("Ordres en attente")

        for order in open_orders:
            col1, col2, col3 = st.columns([4, 1, 1])

            with col1:
                st.write(
                    f"{order['type']} sur {order['actif']} — "
                    f"Prix cible : {order['prix_cible']} — "
                    f"Quantité : {order['quantite']} — "
                    f"{'Trailing' if order.get('trailing') else ''}"
                )

            with col2:
                if st.button(f"Modifier {order['id']}", key=f"edit_{order['id']}"):
                    st.session_state["edit_order"] = order

            with col3:
                if st.button(f"Supprimer {order['id']}", key=f"del_{order['id']}"):
                    update_order_status(order["id"], "annulé")
                    st.success("Ordre supprimé")
                    st.rerun()

    if "edit_order" in st.session_state:
        order = st.session_state["edit_order"]
        st.subheader(f"Modifier l’ordre {order['id']}")

        new_price = st.number_input("Nouveau prix cible", value=float(order["prix_cible"]))
        new_qty = st.number_input("Nouvelle quantité", min_value=1, value=int(order["quantite"]))
        new_trailing = st.checkbox("Trailing", value=order.get("trailing", False))

        if st.button("Enregistrer les modifications"):
            update_order(order["id"], new_price, new_qty, new_trailing)
            st.success("Ordre modifié")
            del st.session_state["edit_order"]
            st.rerun()

        if st.button("Annuler"):
            del st.session_state["edit_order"]
            st.rerun()

    st.header("Historique des ordres exécutés / annulés")

    history = get_order_history(user_id)
    if history:
        st.table(pd.DataFrame(history))
    else:
        st.info("Aucun ordre exécuté ou annulé pour le moment.")

    st.header("Mon Portefeuille")

    df_p = pd.DataFrame({
        "Actif": market_data.columns,
        "Quantité": [positions[a] for a in market_data.columns],
        "Prix": [prix_actuels[a] for a in market_data.columns]
    })

    df_p["Valeur ($)"] = df_p["Quantité"] * df_p["Prix"]

    st.dataframe(df_p[df_p["Quantité"] > 0])

    val_totale = df_p["Valeur ($)"].sum() + current_cash

    st.metric("Cash disponible", f"{current_cash:,.2f} $")
    st.metric("Valeur Totale", f"{val_totale:,.2f} $")

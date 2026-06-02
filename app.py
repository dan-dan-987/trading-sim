import random
import pandas as pd
import streamlit as st

from db import supabase, get_user_data, get_history, calculate_positions, save_transaction
from market import load_market_data
from orders import get_open_orders, save_order, check_orders
from strategies import apply_auto_strategy


# INIT SESSION STATE

if "auto_strategy_active" not in st.session_state:
    st.session_state.auto_strategy_active = False

if "auto_actif" not in st.session_state:
    st.session_state.auto_actif = None


# AUTHENTIFICATION

st.sidebar.title("Compte Trading")

if "user" not in st.session_state:
    menu = ["Connexion", "Inscription"]
    choice = st.sidebar.selectbox("Menu", menu)
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Mot de passe", type="password")

    if choice == "Inscription":
        if st.sidebar.button("Créer mon compte"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("Compte créé ! Connectez-vous.")
            except Exception as e:
                st.sidebar.error(f"Erreur : {e}")

    else:
        if st.sidebar.button("Se connecter"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.sidebar.error("Identifiants incorrects.")

else:
    if st.sidebar.button("Se déconnecter"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()


# APPLICATION PRINCIPALE

if "user" in st.session_state:

    u_id = st.session_state.user.id
    st.title("Simulation de marché et trading virtuel")

    # Chargement des données
    market_data = load_market_data()

    # Initialisation du temps caché
    if "start_index" not in st.session_state:
        st.session_state.start_index = random.randint(0, len(market_data) - 200)

    if "current_index" not in st.session_state:
        st.session_state.current_index = st.session_state.start_index


    # AVANCEMENT DANS LE TEMPS
   
    st.subheader("Avancer dans le temps")

    nb_jours = st.number_input("Nombre de jours à avancer", min_value=1, max_value=200, value=10)

    if st.button("Avancer"):
        old_index = st.session_state.current_index
        new_index = min(st.session_state.current_index + nb_jours, len(market_data) - 1)
        st.session_state.current_index = new_index

        # Simulation jour par jour
        if st.session_state.auto_strategy_active and st.session_state.auto_actif is not None:

            actif = st.session_state.auto_actif

            for i in range(old_index, new_index):
                window = market_data.iloc[st.session_state.start_index:i+1]
                prix_jour = window.iloc[-1]

                history_df = get_history(u_id)
                positions = calculate_positions(history_df, market_data.columns)

                apply_auto_strategy(u_id, window, actif, prix_jour, positions)


    # DONNÉES DU JOUR
   
    jour = st.session_state.current_index
    subset = market_data.iloc[st.session_state.start_index:jour + 1]
    prix_actuels = subset.iloc[-1]

    current_cash = get_user_data(u_id)
    history_df = get_history(u_id)
    positions = calculate_positions(history_df, market_data.columns)


    # ORDRES AVANCÉS
    #
    check_orders(u_id, prix_actuels)

    current_cash = get_user_data(u_id)
    history_df = get_history(u_id)
    positions = calculate_positions(history_df, market_data.columns)


    # GRAPHIQUE
    
    actifs = st.multiselect("Actifs à afficher", market_data.columns.tolist(), default=["Bitcoin"])
    st.line_chart(subset[actifs])


    # TRADING MANUEL
    
    st.header("Trading manuel")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        actif_sel = st.selectbox("Sélectionne un actif", market_data.columns)
        quantite = st.number_input("Quantité", min_value=1, value=1)

    prix_unitaire = prix_actuels[actif_sel]

    with col_t2:
        st.write(f"Prix actuel : **{prix_unitaire:.2f} $**")
        st.write(f"Total opération : **{(prix_unitaire * quantite):,.2f} $**")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("ACHETER", use_container_width=True):
            cout = prix_unitaire * quantite
            if current_cash >= cout:
                save_transaction(u_id, "Achat", actif_sel, quantite, prix_unitaire, current_cash - cout)
                st.success("Achat effectué !")
                st.rerun()
            else:
                st.error("Fonds insuffisants.")

    with c2:
        if st.button("VENDRE", use_container_width=True):
            if positions.get(actif_sel, 0) >= quantite:
                gain = prix_unitaire * quantite
                save_transaction(u_id, "Vente", actif_sel, quantite, prix_unitaire, current_cash + gain)
                st.success("Vente effectuée !")
                st.rerun()
            else:
                st.error("Pas assez de titres.")


    # ORDRES AVANCÉS
    
    st.header("Ordres avancés")

    col_o1, col_o2, col_o3 = st.columns(3)
    with col_o1:
        type_ordre = st.selectbox("Type d’ordre", ["Limit", "Stop-Loss", "Take-Profit"])
    with col_o2:
        prix_cible = st.number_input("Prix cible", min_value=0.0, value=float(prix_unitaire))
    with col_o3:
        quantite_ordre = st.number_input("Quantité ordre", min_value=1, value=1)

    if st.button("Placer l’ordre avancé"):
        save_order(u_id, actif_sel, type_ordre, prix_cible, quantite_ordre)
        st.success("Ordre avancé placé !")

    open_orders = get_open_orders(u_id)
    if open_orders:
        st.subheader("Ordres en attente")
        st.table(pd.DataFrame(open_orders))


    # STRATÉGIES AUTOMATIQUES
   
    st.header("Stratégies automatiques")

    if st.session_state.auto_strategy_active and st.session_state.auto_actif is not None:
        st.success(f"Stratégie SMA 20/50 ACTIVÉE sur {st.session_state.auto_actif}")
    else:
        st.info("Stratégie SMA 20/50 désactivée")

    auto_actif = st.selectbox("Actif pour la stratégie automatique", market_data.columns)
    st.session_state.auto_actif = auto_actif

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        if st.button("Activer la stratégie"):
            st.session_state.auto_strategy_active = True
            st.success("Stratégie activée")

    with col_s2:
        if st.button("Désactiver la stratégie"):
            st.session_state.auto_strategy_active = False
            st.warning("Stratégie désactivée")


    # PORTEFEUILLE
    
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


else:
    st.info("Veuillez vous connecter via la barre latérale pour accéder à votre portefeuille.")

import pandas as pd
from db import supabase, get_user_data, get_history, calculate_positions, save_transaction


def get_open_orders(user_id: str):
    res = supabase.table("orders").select("*").eq("user_id", user_id).eq("statut", "en_attente").execute()
    return res.data


def save_order(user_id: str, actif: str, type_ordre: str, prix_cible: float, quantite: int) -> None:
    supabase.table("orders").insert({
        "user_id": user_id,
        "actif": actif,
        "type": type_ordre,
        "prix_cible": prix_cible,
        "quantite": quantite,
        "statut": "en_attente"
    }).execute()


def update_order_status(order_id: int, statut: str) -> None:
    supabase.table("orders").update({"statut": statut}).eq("id", order_id).execute()


def check_orders(user_id: str, prix_actuels: pd.Series) -> None:
    orders = get_open_orders(user_id)
    for order in orders:
        actif = order["actif"]
        if actif not in prix_actuels.index:
            continue

        prix = prix_actuels[actif]
        cible = order["prix_cible"]
        qte = order["quantite"]
        type_ordre = order["type"]

        should_execute = False
        sens = None

        if type_ordre == "Limit" and prix <= cible:
            should_execute = True
            sens = "Achat"
        elif type_ordre == "Stop-Loss" and prix <= cible:
            should_execute = True
            sens = "Vente"
        elif type_ordre == "Take-Profit" and prix >= cible:
            should_execute = True
            sens = "Vente"

        if should_execute and sens is not None:
            current_cash = get_user_data(user_id)
            history_df = get_history(user_id)
            positions = calculate_positions(history_df, prix_actuels.index)

            if sens == "Achat":
                cout = prix * qte
                if current_cash >= cout:
                    save_transaction(user_id, "Achat", actif, qte, prix, current_cash - cout)
                    update_order_status(order["id"], "executé")
            else:
                if positions.get(actif, 0) >= qte:
                    gain = prix * qte
                    save_transaction(user_id, "Vente", actif, qte, prix, current_cash + gain)
                    update_order_status(order["id"], "executé")

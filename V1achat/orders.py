from db import supabase, get_user_data, save_transaction


#  CREATION D'UN ORDRE
def save_order(user_id, actif, type_ordre, prix_cible, quantite, trailing=False):
    supabase.table("orders").insert({
        "user_id": user_id,
        "actif": actif,
        "type": type_ordre,
        "prix_cible": prix_cible,
        "quantite": quantite,
        "trailing": trailing,
        "highest_price": prix_cible if trailing else None,
        "status": "open"
    }).execute()


#  RECUPERATION DES ORDRES
def get_open_orders(user_id):
    res = supabase.table("orders").select("*").eq("user_id", user_id).eq("status", "open").execute()
    return res.data


def get_order_history(user_id):
    res = supabase.table("orders").select("*").eq("user_id", user_id).neq("status", "open").execute()
    return res.data


#  MODIFICATION D'UN ORDRE
def update_order(order_id, prix_cible, quantite, trailing):
    supabase.table("orders").update({
        "prix_cible": prix_cible,
        "quantite": quantite,
        "trailing": trailing
    }).eq("id", order_id).execute()


def update_order_status(order_id, status):
    supabase.table("orders").update({"status": status}).eq("id", order_id).execute()


#  EXECUTION D'UN ORDRE
def executer_order(order, prix_actuel):
    user_id = order["user_id"]
    actif = order["actif"]
    quantite = order["quantite"]

    cash = get_user_data(user_id)

    # Vente (tous les ordres avancés sont des ventes dans ton système)
    save_transaction(
        user_id,
        "Vente",
        actif,
        quantite,
        prix_actuel,
        cash + prix_actuel * quantite
    )

    update_order_status(order["id"], "executed")


#  LOGIQUE DU TRAILING STOP PROFESSIONNEL
def check_orders(user_id, prix_actuels):
    orders = get_open_orders(user_id)

    for order in orders:
        actif = order["actif"]
        prix = prix_actuels[actif]

        # TRAILING STOP
        if order.get("trailing"):
            highest = order.get("highest_price") or prix

            if prix > highest:
                highest = prix
                new_stop = highest * 0.95  

                supabase.table("orders").update({
                    "highest_price": highest,
                    "prix_cible": new_stop
                }).eq("id", order["id"]).execute()

            if prix <= order["prix_cible"]:
                executer_order(order, prix)
                continue

        # ORDRES CLASSIQUES
        if order["type"] == "Stop-Loss" and prix <= order["prix_cible"]:
            executer_order(order, prix)

        if order["type"] == "Take-Profit" and prix >= order["prix_cible"]:
            executer_order(order, prix)

        if order["type"] == "Limit" and prix <= order["prix_cible"]:
            executer_order(order, prix)

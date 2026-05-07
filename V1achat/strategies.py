import pandas as pd
from db import get_user_data, save_transaction


def strategy_sma_cross(data: pd.DataFrame, actif: str):
    d = data[actif]
    if len(d) < 60:
        return None
    sma20 = d.rolling(20).mean()
    sma50 = d.rolling(50).mean()

    if sma20.iloc[-2] < sma50.iloc[-2] and sma20.iloc[-1] > sma50.iloc[-1]:
        return "buy"
    if sma20.iloc[-2] > sma50.iloc[-2] and sma20.iloc[-1] < sma50.iloc[-1]:
        return "sell"
    return None


def apply_auto_strategy(user_id: str, subset: pd.DataFrame, actif: str,
                        prix_actuels: pd.Series, positions: dict) -> None:
    signal = strategy_sma_cross(subset, actif)
    if signal is None:
        return

    current_cash = get_user_data(user_id)
    prix = prix_actuels[actif]

    if signal == "buy":
        if current_cash >= prix:
            save_transaction(user_id, "Achat", actif, 1, prix, current_cash - prix)
    elif signal == "sell":
        if positions.get(actif, 0) > 0:
            save_transaction(user_id, "Vente", actif, 1, prix, current_cash + prix)

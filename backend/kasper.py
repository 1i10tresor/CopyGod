from telethon import TelegramClient
from dotenv import load_dotenv
import os
import asyncio
import re
from openai import AsyncOpenAI
from telethon import events
from telethon.tl.types import PeerChannel
import MetaTrader5 as mt5
import os 
from datetime import datetime, timedelta
import time
import ast
from kasper import *
import json
load_dotenv()
api_id = os.getenv('api_id')  
api_hash = os.getenv('api_hash')  
gpt_key = os.getenv('GPT_KEY')
client_gpt = AsyncOpenAI(api_key=gpt_key)
client = TelegramClient('anon', api_id, api_hash)
mt5_login = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PSWRD")
mt5_server = os.getenv("MT5_SERVEUR")
expire_date = datetime.now() + timedelta(minutes=10)
expiration_timestamp = int(time.mktime(expire_date.timetuple()))
channel_ids = [-2259371711, -1770543299, -2507130648, -1441894073, -1951792433, -1428690627, -1260132661, -1626843631]
indo_channel_ids = [2507130648, 1441894073, 1951792433, 1428690627, 1260132661, 1626843631 ]
kasper_id = -2259371711

async def signal_or_modify(message):
    if not mt5.initialize():
        print("Échec de l'initialisation de MetaTrader 5.")
        return False
    message_id = message.id
    message = message.text
    if message:
        pattern = re.compile(r'^\s*(buy|sell)\s+(btc|btcusd|bitcoin|gold|xau|xauusd)\s*(now)?\s*$', re.IGNORECASE)
        if pattern.match(message):
            await signal_kasper(message, message_id)
        else:
            with open("pendingKasper.json", "r", encoding="utf-8") as f:
                is_pending = json.load(f)
            if is_pending["pending_order"] is True:
                await modify_order(message, message_id,is_pending)
                with open("pendingKasper.json", "w", encoding="utf-8") as f:
                    json.dump({"pending_order": False}, f)
                return
            else:
                print("Aucun ordre en cours et le message n'est pas un signal de première instance.")
                return
    else:
        print("Le message est vide.")
        return




async def modify_order(message, message_id, is_pending):
    symbol = is_pending["symbol"]
    message_id_signal = is_pending["message_id"]
    order_ids = is_pending["order_ids"]
    if message_id == message_id_signal+1:
        has_sl = re.search(r"(?i)sl|stop\s*loss", message)
        has_tp = re.search(r"(?i)tp|take\s*profit", message)
        if has_sl and has_tp:
            prompt = f"""
                Tu es un expert en analyse de signaux de trading MetaTrader 5.

                Analyse le message Telegram suivant et, si c'est un signal de trading valide, extraits-en les composants :

                \"\"\"{message}\"\"\"

                Règles strictes :
                1. Le message doit contenir :
                - Un prix d'entrée (Entry)
                - Un Stop Loss (SL)
                - Au moins un Take Profit (TP)
                - Un symbole d'actif (actif)

                2. Validations :
                - Pour un BUY :
                    - SL doitêtre inférieur à Entry
                    - Chaque TP doit'être supérieur à Entry
                - Pour un SELL :
                    - SL doitêtre supérieur à Entry
                    - Chaque TP doit'être inférieur à Entry
                - Aucun champ ne doit être inventé. Si une valeur est absente ou ambigüe, retourne `False`.

                Réponse STRICTE : 
                - Si les conditions sont remplies, retourne UNIQUEMENT un dictionnaire avec ce format :
                {{
                "sens": 0|1,             // 0 = BUY, 1 = SELL
                "actif": "SYMBOLE",      // ex: XAUUSD ou BTCUSD. L'actif doit être au format paire de trading completement en majuscules => pour l'or = XAUUSD, pour le bitcoin = BTCUSD
                "SL": "prix",            // string
                "Entry": "prix",         // string
                "TP": ["tp1", "tp2", "tp3"]     // Liste de 1 à 3 TP (strings)
                }}

                - Sinon, retourne simplement : false

                Pas de commentaires, pas de texte additionnel. Seulement le dictionnaire ou false.
                """
            print("Envoi du prompt à GPT-4...")        
            response = await client_gpt.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "user", "content": prompt}])
            match = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL)
            response_text = ast.literal_eval(match.group(0)) if match else None
            print("Reponse de GPT-4:", response_text)
            actual_positions = mt5.positions_get() 
            actual_positions_tickets = [position.ticket for position in actual_positions]
            print(actual_positions_tickets)
            print(f"{len(order_ids)} - vs - {len(response_text["TP"])}")
            print(f"{is_pending['sens']} - vs - {response_text['sens']}")
            print(f"{is_pending['symbol']} - vs - {response_text['actif']}")

            if response_text and len(response_text["TP"]) == len(order_ids) and response_text["sens"] == is_pending["sens"] and response_text["actif"] == is_pending["symbol"]:
                for i, tp in enumerate(response_text["TP"]): 
                    if order_ids[i] in actual_positions_tickets:
                        print(f"Ordre {i} en couurs de modif ...")
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": order_ids[i],
                            "sl": float(response_text["SL"]),
                            "tp": float(tp)}
                        order_modified = mt5.order_send(request)
                        print(mt5.last_error())
                        if order_modified.retcode != mt5.TRADE_RETCODE_DONE:
                            print(f"Erreur lors de la modification de l'ordre: {order_modified.retcode} : {mt5.last_error()}")
                            return
                        print(f"Ordre modifié, ID: {order_ids[i]}, SL: {response_text['SL']}, TP: {response_text['TP']}")
                    else:
                        print(f"Ordre non trouvé, ID: {order_ids[i]}")
            else:
                print(f"La modification des l'ordre a echoué {mt5.last_error()}.")
                return
        else :
            print("Le message n'est pas un signal de modification d'ordre.")
            return


async def signal_kasper(message, message_id):
    pattern = re.compile(r'^\s*(buy|sell)\s+(btc|btcusd|bitcoin|gold|xau|xauusd)\s*(now)?\s*$', re.IGNORECASE)
    if pattern.match(message):
        if "buy" in message.lower():
            print("Signal d'achat détecté.")
            if "xau" in message.lower() or "gold" in message.lower():
                symbol = "XAUUSD"
                price = mt5.symbol_info_tick(symbol).ask
                if price is None:
                    print("Erreur lors de la récupération du prix de l'or.")
                    return False
                sens = mt5.ORDER_TYPE_BUY
                tps = [price + 4, price + 8, price + 12]
                sl = price - 4
                print(f"Un ordre va être envoyé pour l'or, à l'achat, prix actuel: {price}, TP: {tps}, SL: {sl}")
                await send_order_kasper(symbol, price, sl, tps, sens, message_id)
            elif "btc" in message.lower() or "bitcoin" in message.lower():
                symbol = "BTCUSD"
                price = mt5.symbol_info_tick(symbol).ask
                if price is None:
                    print("Erreur lors de la récupération du prix de Bitcoin.")
                    return False
                sens = mt5.ORDER_TYPE_BUY
                tps = [price + 400, price + 800, price + 1200]
                sl = price - 400
                print(f"Un ordre va être envoyé pour Bitcoin, à l'achat, prix actuel: {price}, TP: {tps}, SL: {sl}")
                await send_order_kasper(symbol, price, sl, tps, sens, message_id)
            else:
                print("Achat d'un symbole inconnu.")
                return False
        elif "sell" in message.lower():
            print("Signal de vente détecté.")
            if "xau" in message.lower() or "gold" in message.lower():
                symbol = "XAUUSD"
                price = mt5.symbol_info_tick(symbol).bid
                if price is None:
                    print("Erreur lors de la récupération du prix de l'or.")
                    return False
                sens = mt5.ORDER_TYPE_SELL
                tps = [price - 4, price - 8, price - 12]
                sl = price + 4
                print(f"Un ordre va être envoyé pour l'or, à la vente, prix actuel: {price}, TP: {tps}, SL: {sl}")
                await send_order_kasper(symbol, price, sl, tps, sens, message_id)
            elif "btc" in message.lower() or "bitcoin" in message.lower():
                symbol = "BTCUSD"
                price = mt5.symbol_info_tick(symbol).bid
                if price is None:
                    print("Erreur lors de la récupération du prix de Bitcoin.")
                    return False
                sens = mt5.ORDER_TYPE_SELL
                tps = [price - 400, price - 800, price - 1200]
                sl = price + 400
                print(f"Un ordre va'être envoyé pour Bitcoin, à la vente, prix actuel: {price}, TP: {tps}, SL: {sl}")
                await send_order_kasper(symbol, price, sl, tps, sens, message_id)
            else:
                print("Vente d'un symbole inconnu.")
                return False
        else:
            print("Aucun signal d'achat ou de vente détecté.")
            return False
    else:
        print("Signal mauvais, pas d'achat.")
        return False

async def send_order_kasper(symbol, price, sl, tps, sens, message_id):
    order_ids = []
    lot_size = 0.01
    for i, tp in enumerate(tps): 
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot_size),
            "type": sens, 
            "price": float(price), 
            "sl": float(sl), 
            "tp": float(tp), 
            "deviation": 1,
            "magic": int(message_id), 
            "comment": "Signal sans détails Kasper",
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        order = mt5.order_send(request)
        if order.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Erreur lors de l'envoi de l'ordre: {order.retcode} : {mt5.last_error()}")
            return False  
        order_ids.append(order.order)  
        print(f"Ordre {i+1} envoyé avec succès.")
    pending_kasper = {"pending_order": True,
                        "symbol": symbol,
                        "message_id": message_id,
                        "order_ids": order_ids,
                        "sens": 0 if sens == mt5.ORDER_TYPE_BUY else 1
                        }
    with open("pendingKasper.json", "w", encoding="utf-8") as f:
        json.dump(pending_kasper, f, indent=4)

    




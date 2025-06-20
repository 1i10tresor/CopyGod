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
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Validation des variables d'environnement
required_env_vars = ['api_id', 'api_hash', 'GPT_KEY', 'MT5_LOGIN', 'MT5_PSWRD', 'MT5_SERVEUR']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Variables d'environnement manquantes: {missing_vars}")
    raise ValueError(f"Variables d'environnement manquantes: {missing_vars}")

api_id = os.getenv('api_id')  
api_hash = os.getenv('api_hash')  
gpt_key = os.getenv('GPT_KEY')

try:
    client_gpt = AsyncOpenAI(api_key=gpt_key)
    client = TelegramClient('anon', api_id, api_hash)
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation des clients: {e}")
    raise

mt5_login = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PSWRD")
mt5_server = os.getenv("MT5_SERVEUR")

try:
    expire_date = datetime.now() + timedelta(minutes=10)
    expiration_timestamp = int(time.mktime(expire_date.timetuple()))
except Exception as e:
    logger.error(f"Erreur lors du calcul de la date d'expiration: {e}")
    expiration_timestamp = None

channel_ids = [-2259371711, -1770543299, -2507130648, -1441894073, -1951792433, -1428690627, -1260132661, -1626843631]
indo_channel_ids = [2507130648, 1441894073, 1951792433, 1428690627, 1260132661, 1626843631 ]
kasper_id = -2259371711

# Variable globale pour le monitoring du break even
break_even_monitoring = {}

async def signal_or_modify(message):
    try:
        if not mt5.initialize():
            logger.error("Échec de l'initialisation de MetaTrader 5.")
            return False
            
        if not hasattr(message, 'id') or not hasattr(message, 'text'):
            logger.error("Message invalide reçu")
            return False
            
        message_id = message.id
        message_text = message.text
        
        if not message_text:
            logger.warning("Le message est vide.")
            return False
            
        pattern = re.compile(r'^\s*(buy|sell)\s+(btc|btcusd|bitcoin|gold|xau|xauusd)\s*(now)?\s*$', re.IGNORECASE)
        if pattern.match(message_text):
            return await signal_kasper(message_text, message_id)
        else:
            try:
                with open("pendingKasper.json", "r", encoding="utf-8") as f:
                    is_pending = json.load(f)
            except FileNotFoundError:
                logger.warning("Fichier pendingKasper.json non trouvé, création d'un état par défaut")
                is_pending = {"pending_order": False}
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de décodage JSON dans pendingKasper.json: {e}")
                is_pending = {"pending_order": False}
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de pendingKasper.json: {e}")
                return False
                
            if is_pending.get("pending_order", False):
                logger.info(f"Ordre en attente détecté, récupération de l'ID du message: {message_id}")
                logger.info("Attente de 20 secondes avant de récupérer le contenu du message...")
                await asyncio.sleep(20)
                logger.info("Fin de l'attente, récupération du contenu du message...")
                
                try:
                    kasper_entity = await client.get_entity(kasper_id)
                    updated_message = await client.get_messages(kasper_entity, ids=message_id)
                    if updated_message and updated_message.text:
                        updated_message_text = updated_message.text
                        logger.info(f"Contenu du message récupéré après attente (ID: {message_id}): {updated_message_text[:100]}...")
                        await modify_order(updated_message_text, message_id, is_pending)
                    else:
                        logger.warning(f"Impossible de récupérer le contenu du message ID {message_id}")
                        await modify_order(message_text, message_id, is_pending)
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du message ID {message_id}: {e}")
                    await modify_order(message_text, message_id, is_pending)
                
                try:
                    with open("pendingKasper.json", "w", encoding="utf-8") as f:
                        json.dump({"pending_order": False}, f)
                except Exception as e:
                    logger.error(f"Erreur lors de l'écriture dans pendingKasper.json: {e}")
                return
            else:
                logger.info("Aucun ordre en cours et le message n'est pas un signal de première instance.")
                return
                
    except Exception as e:
        logger.error(f"Erreur dans signal_or_modify: {e}")
        return False


def safe_float_conversion(value, field_name="valeur"):
    """
    Convertit une valeur en float de manière sécurisée
    """
    try:
        if isinstance(value, str):
            # Nettoyer la chaîne (supprimer espaces, virgules, etc.)
            cleaned_value = value.replace(" ", "").replace(",", "")
            return float(cleaned_value)
        elif isinstance(value, (int, float)):
            return float(value)
        else:
            logger.error(f"Type de données non supporté pour {field_name}: {type(value)}")
            return None
    except (ValueError, TypeError) as e:
        logger.error(f"Erreur de conversion en float pour {field_name} '{value}': {e}")
        return None


async def modify_order(message, message_id, is_pending):
    try:
        # Validation des données pending
        required_keys = ["symbol", "message_id", "order_ids", "sens"]
        missing_keys = [key for key in required_keys if key not in is_pending]
        if missing_keys:
            logger.error(f"Clés manquantes dans is_pending: {missing_keys}")
            return
            
        symbol = is_pending["symbol"]
        message_id_signal = is_pending["message_id"]
        order_ids = is_pending["order_ids"]
        
        if not isinstance(order_ids, list) or not order_ids:
            logger.error("order_ids invalide ou vide")
            return
            
        # Vérification que le message est bien le message +1
        if message_id != message_id_signal + 1:
            logger.warning(f"ID de message non séquentiel: attendu {message_id_signal + 1}, reçu {message_id}")
            return
            
        logger.info(f"Traitement du message de modification: ID {message_id} (signal original: {message_id_signal})")
        
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
                    - SL doit être inférieur à Entry
                    - Chaque TP doit être supérieur à Entry
                - Pour un SELL :
                    - SL doit être supérieur à Entry
                    - Chaque TP doit être inférieur à Entry
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
                
            logger.info("Envoi du prompt à GPT-4...")
            
            try:
                response = await client_gpt.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=30
                )
            except Exception as e:
                logger.error(f"Erreur lors de l'appel à GPT-4: {e}")
                return
                
            try:
                match = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL)
                response_text = ast.literal_eval(match.group(0)) if match else None
            except (ValueError, SyntaxError, AttributeError) as e:
                logger.error(f"Erreur lors du parsing de la réponse GPT-4: {e}")
                return
            except Exception as e:
                logger.error(f"Erreur inattendue lors du traitement de la réponse GPT-4: {e}")
                return
                
            logger.info(f"Réponse de GPT-4: {response_text}")
            
            try:
                actual_positions = mt5.positions_get() 
                if actual_positions is None:
                    logger.error("Impossible de récupérer les positions actuelles")
                    return
                actual_positions_tickets = [position.ticket for position in actual_positions]
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des positions: {e}")
                return
                
            logger.info(f"Positions actuelles: {actual_positions_tickets}")
            
            if not response_text or not isinstance(response_text, dict):
                logger.error("Réponse GPT-4 invalide")
                return
                
            # Validation des données de réponse
            required_response_keys = ["TP", "sens", "actif", "SL", "Entry"]
            missing_response_keys = [key for key in required_response_keys if key not in response_text]
            if missing_response_keys:
                logger.error(f"Clés manquantes dans la réponse GPT-4: {missing_response_keys}")
                return
            
            logger.info(f"{len(order_ids)} ordres vs {len(response_text['TP'])} TP")
            logger.info(f"Sens: {is_pending['sens']} vs {response_text['sens']}")
            logger.info(f"Symbole: {is_pending['symbol']} vs {response_text['actif']}")

            if (len(response_text["TP"]) == len(order_ids) and 
                response_text["sens"] == is_pending["sens"] and 
                response_text["actif"] == is_pending["symbol"]):
                
                # Conversion sécurisée des prix
                entry_price = safe_float_conversion(response_text["Entry"], "Entry")
                sl_price = safe_float_conversion(response_text["SL"], "SL")
                
                if entry_price is None or sl_price is None:
                    logger.error("Erreur de conversion des prix Entry ou SL")
                    return
                
                for i, tp in enumerate(response_text["TP"]): 
                    if i >= len(order_ids):
                        logger.warning(f"Index {i} dépasse le nombre d'ordres disponibles")
                        break
                        
                    if order_ids[i] in actual_positions_tickets:
                        logger.info(f"Modification de l'ordre {i} en cours...")
                        
                        # Conversion sécurisée du TP
                        tp_price = safe_float_conversion(tp, f"TP{i+1}")
                        if tp_price is None:
                            logger.error(f"Erreur de conversion du TP{i+1}: {tp}")
                            continue
                        
                        try:
                            request = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": order_ids[i],
                                "sl": sl_price,
                                "tp": tp_price
                            }
                            
                            order_modified = mt5.order_send(request)
                            if order_modified is None:
                                logger.error(f"Échec de la modification de l'ordre {order_ids[i]}: {mt5.last_error()}")
                                continue
                                
                            if order_modified.retcode != mt5.TRADE_RETCODE_DONE:
                                logger.error(f"Erreur lors de la modification de l'ordre {order_ids[i]}: {order_modified.retcode}")
                                continue
                                
                            logger.info(f"Ordre modifié avec succès, ID: {order_ids[i]}, SL: {sl_price}, TP: {tp_price}")
                            
                            # Démarrer le monitoring du break even pour le premier ordre (TP1)
                            if i == 0:
                                await start_break_even_monitoring(
                                    order_ids[i], 
                                    entry_price, 
                                    tp_price, 
                                    sl_price, 
                                    response_text["sens"], 
                                    symbol
                                )
                            
                        except Exception as e:
                            logger.error(f"Erreur lors de la modification de l'ordre {order_ids[i]}: {e}")
                            continue
                    else:
                        logger.warning(f"Ordre non trouvé dans les positions actuelles, ID: {order_ids[i]}")
            else:
                logger.error("Les paramètres de modification ne correspondent pas aux ordres en cours")
                return
        else:
            logger.info("Le message n'est pas un signal de modification d'ordre.")
            return
            
    except Exception as e:
        logger.error(f"Erreur dans modify_order: {e}")


async def start_break_even_monitoring(position_id, entry_price, tp1_price, sl_price, sens, symbol):
    """
    Démarre le monitoring du break even pour une position
    Quand le cours atteint 3/4 du TP1, le SL est déplacé au break even (entry price)
    """
    try:
        # Validation des types et conversion si nécessaire
        entry_price = safe_float_conversion(entry_price, "entry_price")
        tp1_price = safe_float_conversion(tp1_price, "tp1_price")
        sl_price = safe_float_conversion(sl_price, "sl_price")
        
        if None in [entry_price, tp1_price, sl_price]:
            logger.error("Erreur de conversion des prix pour le break even monitoring")
            return
        
        # Calculer le prix de déclenchement du break even (3/4 du chemin vers TP1)
        if sens == 0:  # BUY
            distance_to_tp1 = tp1_price - entry_price
            trigger_price = entry_price + (distance_to_tp1 * 0.75)
        else:  # SELL
            distance_to_tp1 = entry_price - tp1_price
            trigger_price = entry_price - (distance_to_tp1 * 0.75)
        
        logger.info(f"Démarrage du monitoring break even pour la position {position_id}")
        logger.info(f"Prix d'entrée: {entry_price}, TP1: {tp1_price}, Trigger: {trigger_price}")
        
        # Ajouter à la liste de monitoring
        break_even_monitoring[position_id] = {
            "entry_price": entry_price,
            "tp1_price": tp1_price,
            "trigger_price": trigger_price,
            "sens": sens,
            "symbol": symbol,
            "break_even_applied": False
        }
        
        # Démarrer la tâche de monitoring en arrière-plan
        asyncio.create_task(monitor_break_even(position_id))
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du monitoring break even: {e}")


async def monitor_break_even(position_id):
    """
    Surveille en continu le prix pour appliquer le break even
    """
    try:
        logger.info(f"Démarrage du monitoring break even pour la position {position_id}")
        
        while position_id in break_even_monitoring:
            try:
                if break_even_monitoring[position_id]["break_even_applied"]:
                    logger.info(f"Break even déjà appliqué pour la position {position_id}")
                    break
                    
                # Vérifier si la position existe encore
                positions = mt5.positions_get()
                if positions is None:
                    logger.error("Impossible de récupérer les positions pour le monitoring break even")
                    break
                    
                position_exists = any(pos.ticket == position_id for pos in positions)
                if not position_exists:
                    logger.info(f"Position {position_id} fermée, arrêt du monitoring break even")
                    break
                
                # Récupérer le prix actuel
                symbol = break_even_monitoring[position_id]["symbol"]
                tick_info = mt5.symbol_info_tick(symbol)
                if tick_info is None:
                    logger.error(f"Impossible de récupérer le prix pour {symbol}")
                    await asyncio.sleep(5)
                    continue
                
                current_price = tick_info.bid if break_even_monitoring[position_id]["sens"] == 0 else tick_info.ask
                trigger_price = break_even_monitoring[position_id]["trigger_price"]
                entry_price = break_even_monitoring[position_id]["entry_price"]
                sens = break_even_monitoring[position_id]["sens"]
                
                # Vérifier si le prix a atteint le trigger
                trigger_reached = False
                if sens == 0:  # BUY
                    trigger_reached = current_price >= trigger_price
                else:  # SELL
                    trigger_reached = current_price <= trigger_price
                
                if trigger_reached:
                    logger.info(f"Break even déclenché pour la position {position_id} - Prix actuel: {current_price}, Trigger: {trigger_price}")
                    
                    # Récupérer le TP actuel de la position
                    current_tp = None
                    for pos in positions:
                        if pos.ticket == position_id:
                            current_tp = pos.tp
                            break
                    
                    if current_tp is None:
                        logger.error(f"Impossible de récupérer le TP actuel pour la position {position_id}")
                        break
                    
                    # Modifier le SL au break even
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position_id,
                        "sl": entry_price,
                        "tp": current_tp
                    }
                    
                    order_result = mt5.order_send(request)
                    if order_result and order_result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"✅ Break even appliqué avec succès pour la position {position_id} - SL déplacé à {entry_price}")
                        break_even_monitoring[position_id]["break_even_applied"] = True
                    else:
                        error_info = mt5.last_error() if mt5.last_error() else "Erreur inconnue"
                        logger.error(f"❌ Échec de l'application du break even pour la position {position_id}: {error_info}")
                    
                    break
                
                # Attendre 5 secondes avant la prochaine vérification
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring break even pour la position {position_id}: {e}")
                await asyncio.sleep(5)
                continue
            
    except Exception as e:
        logger.error(f"Erreur dans le monitoring break even pour la position {position_id}: {e}")
    finally:
        # Nettoyer le monitoring
        if position_id in break_even_monitoring:
            del break_even_monitoring[position_id]
            logger.info(f"Monitoring break even terminé pour la position {position_id}")


async def signal_kasper(message, message_id):
    try:
        pattern = re.compile(r'^\s*(buy|sell)\s+(btc|btcusd|bitcoin|gold|xau|xauusd)\s*(now)?\s*$', re.IGNORECASE)
        if not pattern.match(message):
            logger.error("Le message ne correspond pas au pattern de signal")
            return False
            
        if "buy" in message.lower():
            logger.info("Signal d'achat détecté.")
            if "xau" in message.lower() or "gold" in message.lower():
                symbol = "XAUUSD"
                try:
                    tick_info = mt5.symbol_info_tick(symbol)
                    if tick_info is None:
                        logger.error("Impossible de récupérer les informations de tick pour XAUUSD")
                        return False
                    price = tick_info.ask
                    if price is None or price <= 0:
                        logger.error(f"Prix invalide pour XAUUSD: {price}")
                        return False
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du prix de l'or: {e}")
                    return False
                    
                sens = mt5.ORDER_TYPE_BUY
                tps = [price + 4, price + 8, price + 12]
                sl = price - 4
                logger.info(f"Ordre XAUUSD BUY - Prix: {price}, TP: {tps}, SL: {sl}")
                return await send_order_kasper(symbol, price, sl, tps, sens, message_id)
                
            elif "btc" in message.lower() or "bitcoin" in message.lower():
                symbol = "BTCUSD"
                try:
                    tick_info = mt5.symbol_info_tick(symbol)
                    if tick_info is None:
                        logger.error("Impossible de récupérer les informations de tick pour BTCUSD")
                        return False
                    price = tick_info.ask
                    if price is None or price <= 0:
                        logger.error(f"Prix invalide pour BTCUSD: {price}")
                        return False
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du prix de Bitcoin: {e}")
                    return False
                    
                sens = mt5.ORDER_TYPE_BUY
                tps = [price + 400, price + 800, price + 1200]
                sl = price - 400
                logger.info(f"Ordre BTCUSD BUY - Prix: {price}, TP: {tps}, SL: {sl}")
                return await send_order_kasper(symbol, price, sl, tps, sens, message_id)
            else:
                logger.error("Symbole d'achat non reconnu")
                return False
                
        elif "sell" in message.lower():
            logger.info("Signal de vente détecté.")
            if "xau" in message.lower() or "gold" in message.lower():
                symbol = "XAUUSD"
                try:
                    tick_info = mt5.symbol_info_tick(symbol)
                    if tick_info is None:
                        logger.error("Impossible de récupérer les informations de tick pour XAUUSD")
                        return False
                    price = tick_info.bid
                    if price is None or price <= 0:
                        logger.error(f"Prix invalide pour XAUUSD: {price}")
                        return False
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du prix de l'or: {e}")
                    return False
                    
                sens = mt5.ORDER_TYPE_SELL
                tps = [price - 4, price - 8, price - 12]
                sl = price + 4
                logger.info(f"Ordre XAUUSD SELL - Prix: {price}, TP: {tps}, SL: {sl}")
                return await send_order_kasper(symbol, price, sl, tps, sens, message_id)
                
            elif "btc" in message.lower() or "bitcoin" in message.lower():
                symbol = "BTCUSD"
                try:
                    tick_info = mt5.symbol_info_tick(symbol)
                    if tick_info is None:
                        logger.error("Impossible de récupérer les informations de tick pour BTCUSD")
                        return False
                    price = tick_info.bid
                    if price is None or price <= 0:
                        logger.error(f"Prix invalide pour BTCUSD: {price}")
                        return False
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du prix de Bitcoin: {e}")
                    return False
                    
                sens = mt5.ORDER_TYPE_SELL
                tps = [price - 400, price - 800, price - 1200]
                sl = price + 400
                logger.info(f"Ordre BTCUSD SELL - Prix: {price}, TP: {tps}, SL: {sl}")
                return await send_order_kasper(symbol, price, sl, tps, sens, message_id)
            else:
                logger.error("Symbole de vente non reconnu")
                return False
        else:
            logger.error("Aucun signal d'achat ou de vente détecté")
            return False
            
    except Exception as e:
        logger.error(f"Erreur dans signal_kasper: {e}")
        return False

async def send_order_kasper(symbol, price, sl, tps, sens, message_id):
    try:
        order_ids = []
        lot_size = 0.01 
        
        # Validation des paramètres
        if not symbol or not isinstance(symbol, str):
            logger.error(f"Symbole invalide: {symbol}")
            return False
            
        if not isinstance(tps, list) or not tps:
            logger.error(f"Liste TP invalide: {tps}")
            return False
            
        if price <= 0 or sl <= 0:
            logger.error(f"Prix ou SL invalide: price={price}, sl={sl}")
            return False
            
        for i, tp in enumerate(tps): 
            try:
                if tp <= 0:
                    logger.error(f"TP invalide à l'index {i}: {tp}")
                    continue
                    
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
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                order = mt5.order_send(request)
                print("response", order)
                print(request)
                if order is None:
                    logger.error(f"Échec de l'envoi de l'ordre {i+1}: {mt5.last_error()}")
                    continue
                    
                if order.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"Erreur lors de l'envoi de l'ordre {i+1}: {order.retcode} - {mt5.last_error()}")
                    continue
                    
                order_ids.append(order.order)  
                logger.info(f"Ordre {i+1} envoyé avec succès, ID: {order.order}")
                
            except (ValueError, TypeError) as e:
                logger.error(f"Erreur de conversion pour l'ordre {i+1}: {e}")
                continue
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'ordre {i+1}: {e}")
                continue
                
        if not order_ids:
            logger.error("Aucun ordre n'a pu être envoyé")
            return False
            
        pending_kasper = {
            "pending_order": True,
            "symbol": symbol,
            "message_id": message_id,
            "order_ids": order_ids,
            "sens": 0 if sens == mt5.ORDER_TYPE_BUY else 1
        }
        
        try:
            with open("pendingKasper.json", "w", encoding="utf-8") as f:
                json.dump(pending_kasper, f, indent=4)
            logger.info(f"État pending sauvegardé: {len(order_ids)} ordres")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'état pending: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"Erreur dans send_order_kasper: {e}")
        return False
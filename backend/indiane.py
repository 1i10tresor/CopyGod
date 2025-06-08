import re
import ast
import logging  # modified
from datetime import datetime, timedelta
import time
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)  # modified

async def est_order(canale, message):
    try:  # modified
        if not hasattr(message, 'text') or not hasattr(message, 'id') or not hasattr(message, 'date'):  # modified
            logger.error("Message invalide reçu")  # modified
            return  # modified
            
        canal = await client.get_entity(-canale)
        if not canal:  # modified
            logger.error(f"Impossible de récupérer l'entité du canal {canale}")  # modified
            return  # modified
            
        if message.text:
            has_sl = re.search(r"(?i)sl|stop\s*loss", message.text)
            has_tp = re.search(r"(?i)tp|take\s*profit", message.text)
            
            if has_sl and has_tp:
                logger.info(f"Message ID: {message.id}, Date: {message.date}, Canal: {canal.id} - {canal.title}")  # modified
                logger.info("Ordre trouvé")  # modified
                
                prompt = f"""
                    Tu es un expert en analyse de signaux de trading MetaTrader 5.

                    Analyse le message Telegram suivant et, si c'est un signal de trading valide, extraits-en les composants :

                    \"\"\"{message.text}\"\"\"

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
                    - Aucun champ ne doit être inventé. Si une valeur est absente ou ambigüe, retourne `false`.

                    Réponse STRICTE :
                    - Si les conditions sont remplies, retourne UNIQUEMENT un dictionnaire avec ce format :
                    {{
                    "sens": 0|1,             // 0 = BUY, 1 = SELL
                    "actif": "SYMBOLE",      // ex: XAUUSD ou BTCUSD. L'actif doit être au format paire de trading completement en majuscules => pour l'or = XAUUSD, pour le bitcoin = BTCUSD
                    "SL": "prix",            // string
                    "Entry": "prix",         // string
                    "TP": ["tp1", "tp2"]     // Liste de 1 à 4 TP (strings)
                    }}

                    - Sinon, retourne simplement : false

                    Pas de commentaires, pas de texte additionnel. Seulement le dictionnaire ou false.
                    """
                    
                logger.info("Envoi du prompt à GPT-4...")  # modified
                
                try:  # modified
                    response = await client_gpt.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        timeout=30  # modified
                    )
                except Exception as e:  # modified
                    logger.error(f"Erreur lors de l'appel à GPT-4: {e}")  # modified
                    return  # modified
                    
                try:  # modified
                    match = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL)
                    response_text = ast.literal_eval(match.group(0)) if match else None
                except (ValueError, SyntaxError, AttributeError) as e:  # modified
                    logger.error(f"Erreur lors du parsing de la réponse GPT-4: {e}")  # modified
                    return  # modified
                except Exception as e:  # modified
                    logger.error(f"Erreur inattendue lors du traitement de la réponse GPT-4: {e}")  # modified
                    return  # modified
                    
                logger.info(f"Réponse GPT-4: {response_text}")  # modified
                
                if response_text:  # modified
                    def_order(response_text, canal)
                else:  # modified
                    logger.warning("Aucun signal valide détecté par GPT-4")  # modified
                    
                logger.info("-" * 40)  # modified
            else:
                logger.info(f"Message ID: {message.id}, Date: {message.date}, Canal: {canal.id} - {canal.title}")  # modified
                logger.info("Pas un ordre de trading.")  # modified
                logger.info("-" * 40)  # modified
        else:
            logger.info(f"Message ID: {message.id}, Date: {message.date}, Canal: {canal.id} - {canal.title}")  # modified
            logger.info("Message vide ou non textuel.")  # modified
            logger.info("-" * 40)  # modified
            
    except Exception as e:  # modified
        logger.error(f"Erreur dans est_order: {e}")  # modified


def def_order(response_text_gpt, canal):
    try:  # modified
        logger.info("Signal bien reçu par def_order, traitement en cours...")  # modified
        
        if response_text_gpt is None:
            logger.warning("Aucun signal de trading valide trouvé dans le message par chatgpt, None retourné.")  # modified
            return
            
        # Validation de la structure de réponse  # modified
        required_keys = ["sens", "SL", "Entry", "actif"]  # modified
        missing_keys = [key for key in required_keys if key not in response_text_gpt]  # modified
        if missing_keys:  # modified
            logger.error(f"Clés manquantes dans la réponse GPT: {missing_keys}")  # modified
            return  # modified
            
        try:  # modified
            response_text = {
                k: [tp.replace(" ", "") for tp in v] if isinstance(v, list)
                else v.replace(" ", "") if isinstance(v, str)
                else v
                for k, v in response_text_gpt.items()
            }
        except Exception as e:  # modified
            logger.error(f"Erreur lors du nettoyage des données: {e}")  # modified
            return  # modified
            
        logger.info(f"Le signal du canal {canal.id}, est dans la liste des canaux indo : {canal.id in indo_channel_ids}")  # modified
        
        if canal.id in indo_channel_ids:
            try:  # modified
                sens = response_text["sens"]
                sl = response_text["SL"]
                entry = response_text["Entry"]
                actif = response_text["actif"]
                
                # Validation des types et valeurs  # modified
                if not isinstance(sens, int) or sens not in [0, 1]:  # modified
                    logger.error(f"Sens invalide: {sens}")  # modified
                    return  # modified
                    
                try:  # modified
                    entry_float = float(entry)
                    sl_float = float(sl)
                    tp = entry_float + (entry_float - sl_float)
                except (ValueError, TypeError) as e:  # modified
                    logger.error(f"Erreur de conversion des prix: {e}")  # modified
                    return  # modified
                    
                if tp <= 0 or entry_float <= 0 or sl_float <= 0:  # modified
                    logger.error(f"Prix invalides: entry={entry_float}, sl={sl_float}, tp={tp}")  # modified
                    return  # modified
                    
                send_order_indo(actif, sl, tp, sens, canal.id, entry)
                
            except KeyError as e:  # modified
                logger.error(f"Clé manquante dans response_text: {e}")  # modified
                return  # modified
            except Exception as e:  # modified
                logger.error(f"Erreur lors du traitement du signal indo: {e}")  # modified
                return  # modified
        else:
            logger.warning(f"Le canal {canal.id} n'est pas dans la liste des canaux indo, ordre non envoyé.")  # modified
            logger.warning("Vérifiez si le canal est autorisé à envoyer des ordres.")  # modified
            return
            
    except Exception as e:  # modified
        logger.error(f"Erreur dans def_order: {e}")  # modified

def send_order_indo(symbol, sl, tp, sens, canal, entry):
    try:  # modified
        # Validation des paramètres d'entrée  # modified
        if not symbol or not isinstance(symbol, str):  # modified
            logger.error(f"Symbole invalide: {symbol}")  # modified
            return  # modified
            
        if symbol not in ["XAUUSD", "BTCUSD"]:  # modified
            logger.error(f"Symbole non supporté: {symbol}")  # modified
            return  # modified
            
        try:  # modified
            expire_date = datetime.now() + timedelta(minutes=10)
            expiration_timestamp = int(time.mktime(expire_date.timetuple()))
        except Exception as e:  # modified
            logger.error(f"Erreur lors du calcul de la date d'expiration: {e}")  # modified
            return  # modified
            
        try:  # modified
            tick_info = mt5.symbol_info_tick(symbol)
            if tick_info is None:  # modified
                logger.error(f"Impossible de récupérer les informations de tick pour {symbol}")  # modified
                return  # modified
                
            price = tick_info.ask if sens == 0 else tick_info.bid
            if price is None or price <= 0:  # modified
                logger.error(f"Prix invalide pour {symbol}: {price}")  # modified
                return  # modified
        except Exception as e:  # modified
            logger.error(f"Erreur lors de la récupération du prix pour {symbol}: {e}")  # modified
            return  # modified
            
        lot_size = 0.01 
        
        try:  # modified
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot_size),
                "type": mt5.ORDER_TYPE_BUY if sens == 0 else mt5.ORDER_TYPE_SELL,
                "price": float(entry),
                "sl": float(sl),
                "tp": float(tp), 
                "deviation": 1 if symbol == "XAUUSD" else 2500 if symbol == "BTCUSD" else 1, 
                "magic": int(canal), 
                "comment": "Order from Telegram CopyGod",
                "type_time": mt5.ORDER_TIME_SPECIFIED,
                "expiration": expiration_timestamp,  
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
        except (ValueError, TypeError) as e:  # modified
            logger.error(f"Erreur lors de la création de la requête d'ordre: {e}")  # modified
            return  # modified
            
        if not commissions_ethyque_indo(request, price):
            logger.warning("❌ Commission non éthique détectée, ordre non envoyé.")  # modified
            return
            
        try:  # modified
            order = mt5.order_send(request)
            if order is None:
                logger.error(f"Échec de l'envoi de l'ordre pour {symbol}. Erreur: {mt5.last_error()}")  # modified
                return  # modified
                
            if order.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info("✅ Ordre passé avec succès.")  # modified
                logger.info(f"Ticket: {order.order}")  # modified
            else:
                logger.error("❌ Échec de l'envoi de l'ordre.")  # modified
                logger.error(f"Code erreur : {order.retcode}")  # modified
                logger.error(f"Description : {order.comment}")  # modified
                
        except Exception as e:  # modified
            logger.error(f"Erreur lors de l'envoi de l'ordre: {e}")  # modified
            
    except Exception as e:  # modified
        logger.error(f"Erreur dans send_order_indo: {e}")  # modified


def commissions_ethyque_indo(request, price):
    try:  # modified
        # Validation des paramètres  # modified
        if not request or not isinstance(request, dict):  # modified
            logger.error("Requête invalide")  # modified
            return False  # modified
            
        required_fields = ["price", "symbol", "deviation", "sl", "tp", "type"]  # modified
        missing_fields = [field for field in required_fields if field not in request]  # modified
        if missing_fields:  # modified
            logger.error(f"Champs manquants dans la requête: {missing_fields}")  # modified
            return False  # modified
            
        try:  # modified
            request_price = float(request["price"])
            market_price = float(price)
            sl_price = float(request["sl"])
            tp_price = float(request["tp"])
        except (ValueError, TypeError) as e:  # modified
            logger.error(f"Erreur de conversion des prix: {e}")  # modified
            return False  # modified
            
        if market_price <= 0 or request_price <= 0:  # modified
            logger.error(f"Prix invalides: market_price={market_price}, request_price={request_price}")  # modified
            return False  # modified
            
        # Vérification de l'écart de prix  # modified
        price_diff_ratio = abs(request_price - market_price) / request_price
        if price_diff_ratio > 0.0035:
            logger.warning(f"Écart trop important entre le prix demandé : {request_price} $ et le prix du marché : {market_price} $.")  # modified
            return False
            
        # Vérification des déviations  # modified
        if request["symbol"] == "XAUUSD" and request["deviation"] > 301:
            logger.warning("Déviation trop importante pour XAUUSD.")  # modified
            return False
        elif request["symbol"] == "BTCUSD" and request["deviation"] > 2501:
            logger.warning("Déviation trop importante pour BTCUSD.")  # modified
            return False
            
        # Vérification de la cohérence SL/TP selon le type d'ordre  # modified
        if request["type"] == 0:  # BUY
            if sl_price > request_price:
                logger.warning("SL supérieur à l'Entry pour un ordre BUY.")  # modified
                return False                
            if tp_price < request_price:
                logger.warning("TP inférieur à l'Entry pour un ordre BUY.")  # modified
                return False
        elif request["type"] == 1:  # SELL
            if sl_price < request_price:
                logger.warning("SL inférieur à l'Entry pour un ordre SELL.")  # modified
                return False
            if tp_price > request_price:
                logger.warning("TP supérieur à l'Entry pour un ordre SELL.")  # modified
                return False
                
        # Vérification des écarts SL et TP  # modified
        sl_diff = abs(request_price - sl_price)
        tp_diff = abs(request_price - tp_price)
        
        if sl_diff > 0.01 * request_price:
            logger.warning(f"Écart trop important entre l'Entry et le SL: {sl_diff} points")  # modified
            return False
            
        if tp_diff > 0.02 * request_price or tp_diff < 0.0008 * request_price:
            logger.warning(f"Écart inapproprié entre l'Entry et le TP : {tp_diff} points")  # modified
            return False
            
        return True
        
    except Exception as e:  # modified
        logger.error(f"Erreur dans commissions_ethyque_indo: {e}")  # modified
        return False  # modified
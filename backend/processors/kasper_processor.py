import re
import json
import logging
from typing import Optional
import MetaTrader5 as mt5
from ..services.gpt_service import GPTService
from ..services.mt5_service import MT5Service
from ..core.config import TradingConfig
from ..models.signal import TradingSignal, OrderType, SignalType, PendingOrder
from ..core.exceptions import TradingBotException

logger = logging.getLogger(__name__)

class KasperProcessor:
    """Processeur spécialisé pour les signaux Kasper"""
    
    def __init__(self, config: TradingConfig, gpt_service: GPTService, mt5_service: MT5Service):
        self.config = config
        self.gpt_service = gpt_service
        self.mt5_service = mt5_service
        self.pending_file = "pendingKasper.json"
    
    async def process_message(self, message):
        """Traite un message du canal Kasper"""
        try:
            if not hasattr(message, 'id') or not hasattr(message, 'text'):
                logger.error("Message invalide reçu")
                return False
            
            message_id = message.id
            message_text = message.text
            
            if not message_text:
                logger.warning("Le message est vide")
                return False
            
            # Vérification si c'est un signal initial
            if self._is_initial_signal(message_text):
                return await self._process_initial_signal(message_text, message_id)
            else:
                # Vérification si c'est une modification
                pending_order = self._load_pending_order()
                if pending_order and pending_order.pending:
                    await self._process_modification(message_text, message_id, pending_order)
                    self._clear_pending_order()
                else:
                    logger.info("Aucun ordre en cours et le message n'est pas un signal initial")
                    
        except Exception as e:
            logger.error(f"Erreur dans le processeur Kasper: {e}")
            raise TradingBotException(f"Erreur Kasper: {e}")
    
    def _is_initial_signal(self, message_text: str) -> bool:
        """Vérifie si c'est un signal initial Kasper"""
        pattern = re.compile(r'^\s*(buy|sell)\s+(btc|btcusd|bitcoin|gold|xau|xauusd)\s*(now)?\s*$', re.IGNORECASE)
        return bool(pattern.match(message_text))
    
    async def _process_initial_signal(self, message_text: str, message_id: int) -> bool:
        """Traite un signal initial"""
        try:
            # Parsing du signal
            if "buy" in message_text.lower():
                order_type = OrderType.BUY
            elif "sell" in message_text.lower():
                order_type = OrderType.SELL
            else:
                logger.error("Type d'ordre non reconnu")
                return False
            
            # Détermination du symbole
            if any(keyword in message_text.lower() for keyword in ["xau", "gold"]):
                symbol = "XAUUSD"
            elif any(keyword in message_text.lower() for keyword in ["btc", "bitcoin"]):
                symbol = "BTCUSD"
            else:
                logger.error("Symbole non reconnu")
                return False
            
            # Récupération du prix
            tick_info = self.mt5_service.get_tick_info(symbol)
            if not tick_info:
                return False
            
            price = tick_info.ask if order_type == OrderType.BUY else tick_info.bid
            
            # Création du signal
            signal = TradingSignal.create_kasper_signal(
                symbol=symbol,
                order_type=order_type,
                price=price,
                channel_id=self.config.kasper_id,
                message_id=message_id
            )
            
            # Envoi des ordres
            order_ids = await self._send_multiple_orders(signal)
            if order_ids:
                # Sauvegarde de l'état pending
                pending_order = PendingOrder(
                    symbol=signal.symbol,
                    message_id=message_id,
                    order_ids=order_ids,
                    order_type=signal.order_type
                )
                self._save_pending_order(pending_order)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du signal initial: {e}")
            return False
    
    async def _send_multiple_orders(self, signal: TradingSignal) -> list:
        """Envoie plusieurs ordres pour un signal"""
        order_ids = []
        
        for i, tp in enumerate(signal.take_profits):
            try:
                request = self.mt5_service.create_order_request(
                    symbol=signal.symbol,
                    volume=signal.lot_size,
                    order_type=mt5.ORDER_TYPE_BUY if signal.order_type == OrderType.BUY else mt5.ORDER_TYPE_SELL,
                    price=signal.entry_price,
                    sl=signal.stop_loss,
                    tp=tp,
                    magic=signal.message_id,
                    comment="Signal Kasper"
                )
                
                order = self.mt5_service.send_order(request)
                if order and order.retcode == mt5.TRADE_RETCODE_DONE:
                    order_ids.append(order.order)
                    logger.info(f"Ordre {i+1} envoyé avec succès, ID: {order.order}")
                else:
                    logger.error(f"Échec de l'envoi de l'ordre {i+1}")
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'ordre {i+1}: {e}")
                continue
        
        return order_ids
    
    async def _process_modification(self, message_text: str, message_id: int, pending_order: PendingOrder):
        """Traite une modification d'ordre"""
        try:
            # Vérification de la séquence des messages
            if message_id != pending_order.message_id + 1:
                logger.warning(f"ID de message non séquentiel: attendu {pending_order.message_id + 1}, reçu {message_id}")
                return
            
            # Vérification que c'est un signal de modification
            has_sl = re.search(r"(?i)sl|stop\s*loss", message_text)
            has_tp = re.search(r"(?i)tp|take\s*profit", message_text)
            
            if not (has_sl and has_tp):
                logger.info("Le message n'est pas un signal de modification")
                return
            
            # Analyse avec GPT
            gpt_response = await self.gpt_service.analyze_signal(message_text, "modification")
            if not gpt_response:
                logger.error("Aucun signal valide détecté par GPT")
                return
            
            # Validation de la cohérence
            if not self._validate_modification(gpt_response, pending_order):
                logger.error("Les paramètres de modification ne correspondent pas")
                return
            
            # Application des modifications
            await self._apply_modifications(gpt_response, pending_order)
            
        except Exception as e:
            logger.error(f"Erreur lors de la modification: {e}")
    
    def _validate_modification(self, gpt_response: dict, pending_order: PendingOrder) -> bool:
        """Valide la cohérence d'une modification"""
        try:
            return (
                len(gpt_response["TP"]) == len(pending_order.order_ids) and
                gpt_response["sens"] == pending_order.order_type.value and
                gpt_response["actif"] == pending_order.symbol
            )
        except KeyError as e:
            logger.error(f"Clé manquante dans la réponse GPT: {e}")
            return False
    
    async def _apply_modifications(self, gpt_response: dict, pending_order: PendingOrder):
        """Applique les modifications aux ordres"""
        try:
            positions = self.mt5_service.get_positions()
            if not positions:
                logger.error("Impossible de récupérer les positions")
                return
            
            position_tickets = [pos.ticket for pos in positions]
            
            for i, tp in enumerate(gpt_response["TP"]):
                if i >= len(pending_order.order_ids):
                    break
                
                order_id = pending_order.order_ids[i]
                if order_id in position_tickets:
                    result = self.mt5_service.modify_position(
                        position_id=order_id,
                        sl=float(gpt_response["SL"]),
                        tp=float(tp)
                    )
                    
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"Ordre modifié avec succès, ID: {order_id}")
                    else:
                        logger.error(f"Échec de la modification de l'ordre {order_id}")
                else:
                    logger.warning(f"Ordre non trouvé dans les positions: {order_id}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'application des modifications: {e}")
    
    def _load_pending_order(self) -> Optional[PendingOrder]:
        """Charge l'ordre en attente depuis le fichier"""
        try:
            with open(self.pending_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PendingOrder.from_dict(data)
        except FileNotFoundError:
            logger.info("Aucun fichier pending trouvé")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du chargement du pending: {e}")
            return None
    
    def _save_pending_order(self, pending_order: PendingOrder):
        """Sauvegarde l'ordre en attente"""
        try:
            with open(self.pending_file, "w", encoding="utf-8") as f:
                json.dump(pending_order.to_dict(), f, indent=4)
            logger.info("État pending sauvegardé")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
    
    def _clear_pending_order(self):
        """Efface l'ordre en attente"""
        try:
            with open(self.pending_file, "w", encoding="utf-8") as f:
                json.dump({"pending_order": False}, f)
            logger.info("État pending effacé")
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement: {e}")
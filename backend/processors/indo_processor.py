import logging
from typing import Optional
import MetaTrader5 as mt5
from ..services.gpt_service import GPTService
from ..services.mt5_service import MT5Service
from ..core.config import TradingConfig
from ..models.signal import TradingSignal, SignalType
from ..validators.order_validator import OrderValidator
from ..core.exceptions import TradingBotException, OrderValidationError

logger = logging.getLogger(__name__)

class IndoProcessor:
    """Processeur spécialisé pour les signaux Indo"""
    
    def __init__(self, config: TradingConfig, gpt_service: GPTService, mt5_service: MT5Service):
        self.config = config
        self.gpt_service = gpt_service
        self.mt5_service = mt5_service
        self.validator = OrderValidator()
    
    async def process_message(self, message, entity):
        """Traite un message des canaux Indo"""
        try:
            if not hasattr(message, 'text') or not hasattr(message, 'id') or not hasattr(message, 'date'):
                logger.error("Message invalide reçu")
                return
            
            if not message.text:
                logger.info("Message vide ou non textuel")
                return
            
            # Vérification si c'est un signal de trading
            if not self._is_trading_signal(message.text):
                logger.info("Pas un signal de trading")
                return
            
            logger.info(f"Signal détecté du canal {entity.id}")
            
            # Analyse avec GPT
            gpt_response = await self.gpt_service.analyze_signal(message.text)
            if not gpt_response:
                logger.warning("Aucun signal valide détecté par GPT")
                return
            
            # Vérification que le canal est autorisé
            if entity.id not in self.config.indo_channel_ids:
                logger.warning(f"Canal {entity.id} non autorisé pour les ordres Indo")
                return
            
            # Traitement du signal
            await self._process_indo_signal(gpt_response, entity.id)
            
        except Exception as e:
            logger.error(f"Erreur dans le processeur Indo: {e}")
            raise TradingBotException(f"Erreur Indo: {e}")
    
    def _is_trading_signal(self, message_text: str) -> bool:
        """Vérifie si c'est un signal de trading"""
        import re
        has_sl = re.search(r"(?i)sl|stop\s*loss", message_text)
        has_tp = re.search(r"(?i)tp|take\s*profit", message_text)
        return bool(has_sl and has_tp)
    
    async def _process_indo_signal(self, gpt_response: dict, channel_id: int):
        """Traite un signal Indo"""
        try:
            # Validation de la structure
            required_keys = ["sens", "SL", "Entry", "actif"]
            missing_keys = [key for key in required_keys if key not in gpt_response]
            if missing_keys:
                logger.error(f"Clés manquantes dans la réponse GPT: {missing_keys}")
                return
            
            # Validation du symbole
            symbol = gpt_response["actif"]
            if not self.validator.validate_symbol(symbol):
                logger.error(f"Symbole non supporté: {symbol}")
                return
            
            # Calcul du TP pour Indo (logique spécifique)
            try:
                entry_price = float(gpt_response["Entry"])
                sl_price = float(gpt_response["SL"])
                tp_price = entry_price + (entry_price - sl_price)  # TP = Entry + (Entry - SL)
                
                if tp_price <= 0:
                    logger.error(f"TP calculé invalide: {tp_price}")
                    return
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Erreur de conversion des prix: {e}")
                return
            
            # Récupération du prix de marché
            tick_info = self.mt5_service.get_tick_info(symbol)
            if not tick_info:
                return
            
            market_price = tick_info.ask if gpt_response["sens"] == 0 else tick_info.bid
            
            # Création de la requête d'ordre
            try:
                request = self.mt5_service.create_order_request(
                    symbol=symbol,
                    volume=self.config.lot_size,
                    order_type=mt5.ORDER_TYPE_BUY if gpt_response["sens"] == 0 else mt5.ORDER_TYPE_SELL,
                    price=entry_price,
                    sl=sl_price,
                    tp=tp_price,
                    magic=channel_id,
                    comment="Order from Telegram Indo"
                )
            except Exception as e:
                logger.error(f"Erreur lors de la création de la requête: {e}")
                return
            
            # Validation éthique
            if not self.validator.validate_order_request(request, market_price):
                logger.warning("❌ Validation éthique échouée, ordre non envoyé")
                return
            
            # Envoi de l'ordre
            order = self.mt5_service.send_order(request)
            if order and order.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info("✅ Ordre Indo passé avec succès")
                logger.info(f"Ticket: {order.order}")
            else:
                logger.error("❌ Échec de l'envoi de l'ordre Indo")
                if order:
                    logger.error(f"Code erreur: {order.retcode}")
                    
        except Exception as e:
            logger.error(f"Erreur lors du traitement du signal Indo: {e}")
            raise OrderValidationError(f"Erreur de traitement: {e}")
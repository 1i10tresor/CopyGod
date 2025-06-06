import re
import logging
from typing import Optional
from ..services.telegram_service import TelegramService
from ..services.gpt_service import GPTService
from ..services.mt5_service import MT5Service
from ..processors.kasper_processor import KasperProcessor
from ..processors.indo_processor import IndoProcessor
from ..core.config import TradingConfig
from ..core.exceptions import TradingBotException

logger = logging.getLogger(__name__)

class MessageHandler:
    """Gestionnaire principal des messages Telegram"""
    
    def __init__(self, config: TradingConfig, telegram_service: TelegramService,
                 gpt_service: GPTService, mt5_service: MT5Service):
        self.config = config
        self.telegram_service = telegram_service
        self.gpt_service = gpt_service
        self.mt5_service = mt5_service
        
        # Processeurs spécialisés
        self.kasper_processor = KasperProcessor(config, gpt_service, mt5_service)
        self.indo_processor = IndoProcessor(config, gpt_service, mt5_service)
    
    async def handle_message(self, event, client):
        """Gestionnaire principal des messages"""
        try:
            message = event.message
            entity = await client.get_entity(-event.chat_id)
            
            if not hasattr(message, 'text') or not hasattr(message, 'id') or not hasattr(message, 'date'):
                logger.error("Message invalide reçu")
                return
            
            logger.info(f"Message reçu du canal {entity.id}: {entity.title}")
            
            # Routage selon le canal
            if abs(entity.id) == abs(self.config.kasper_id):
                await self.kasper_processor.process_message(message)
            elif entity.id in self.config.indo_channel_ids:
                await self.indo_processor.process_message(message, entity)
            else:
                logger.warning(f"Message reçu d'un canal non autorisé: {entity.id}")
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message: {e}")
            raise TradingBotException(f"Erreur de traitement: {e}")
    
    def is_trading_signal(self, message_text: str) -> bool:
        """Détermine si un message est un signal de trading"""
        if not message_text:
            return False
            
        # Vérification pour les signaux avec SL et TP
        has_sl = re.search(r"(?i)sl|stop\s*loss", message_text)
        has_tp = re.search(r"(?i)tp|take\s*profit", message_text)
        
        if has_sl and has_tp:
            return True
        
        # Vérification pour les signaux Kasper
        kasper_pattern = re.compile(r'^\s*(buy|sell)\s+(btc|btcusd|bitcoin|gold|xau|xauusd)\s*(now)?\s*$', re.IGNORECASE)
        if kasper_pattern.match(message_text):
            return True
            
        return False
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel
from typing import List, Callable, Optional
import logging
from ..core.config import TradingConfig
from ..core.exceptions import TelegramConnectionError

logger = logging.getLogger(__name__)

class TelegramService:
    """Service de gestion des connexions et messages Telegram"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.client: Optional[TelegramClient] = None
        self.channel_entities = []
        
    async def initialize(self) -> bool:
        """Initialise la connexion Telegram"""
        try:
            self.client = TelegramClient('anon', self.config.api_id, self.config.api_hash)
            
            if not await self.client.start():
                raise TelegramConnectionError("Échec de la connexion au client Telegram")
                
            logger.info("Connexion Telegram réussie")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation Telegram: {e}")
            raise TelegramConnectionError(f"Erreur d'initialisation: {e}")
    
    async def setup_channels(self) -> bool:
        """Configure les entités de canaux"""
        try:
            self.channel_entities = []
            
            for channel_id in self.config.channel_ids:
                try:
                    channel_entity = await self.client.get_entity(PeerChannel(channel_id))
                    self.channel_entities.append(channel_entity)
                    logger.info(f"Canal {channel_id} récupéré avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération du canal ID {channel_id}: {e}")
                    continue
                    
            if not self.channel_entities:
                raise TelegramConnectionError("Aucun canal trouvé")
                
            logger.info(f"{len(self.channel_entities)} canaux configurés")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration des canaux: {e}")
            return False
    
    def register_message_handler(self, handler: Callable):
        """Enregistre un gestionnaire de messages"""
        if not self.client:
            raise TelegramConnectionError("Client non initialisé")
            
        @self.client.on(events.NewMessage(chats=self.channel_entities))
        async def handle_new_message(event):
            try:
                await handler(event, self.client)
            except Exception as e:
                logger.error(f"Erreur dans le gestionnaire de messages: {e}")
    
    async def get_entity(self, channel_id: int):
        """Récupère l'entité d'un canal"""
        if not self.client:
            raise TelegramConnectionError("Client non initialisé")
        return await self.client.get_entity(-channel_id)
    
    async def run(self):
        """Lance le client en mode écoute"""
        if not self.client:
            raise TelegramConnectionError("Client non initialisé")
        await self.client.run_until_disconnected()
    
    async def disconnect(self):
        """Ferme la connexion"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Connexion Telegram fermée")
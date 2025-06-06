import asyncio
import logging
from core.config import TradingConfig
from core.exceptions import TradingBotException, ConfigurationError
from services.telegram_service import TelegramService
from services.mt5_service import MT5Service
from services.gpt_service import GPTService
from handlers.message_handler import MessageHandler

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot_oop.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    """Bot de trading principal utilisant une architecture POO"""
    
    def __init__(self):
        self.config: TradingConfig = None
        self.telegram_service: TelegramService = None
        self.mt5_service: MT5Service = None
        self.gpt_service: GPTService = None
        self.message_handler: MessageHandler = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialise tous les services du bot"""
        try:
            logger.info("🚀 Initialisation du bot de trading...")
            
            # Chargement de la configuration
            self.config = TradingConfig.from_env()
            if not self.config.validate():
                raise ConfigurationError("Configuration invalide")
            logger.info("✅ Configuration chargée et validée")
            
            # Initialisation des services
            await self._initialize_services()
            
            # Configuration du gestionnaire de messages
            self.message_handler = MessageHandler(
                self.config, 
                self.telegram_service, 
                self.gpt_service, 
                self.mt5_service
            )
            
            # Enregistrement du gestionnaire de messages
            self.telegram_service.register_message_handler(
                self.message_handler.handle_message
            )
            
            logger.info("✅ Bot initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation: {e}")
            await self.cleanup()
            raise TradingBotException(f"Erreur d'initialisation: {e}")
    
    async def _initialize_services(self):
        """Initialise tous les services nécessaires"""
        try:
            # Service Telegram
            self.telegram_service = TelegramService(self.config)
            await self.telegram_service.initialize()
            await self.telegram_service.setup_channels()
            logger.info("✅ Service Telegram initialisé")
            
            # Service MT5
            self.mt5_service = MT5Service(self.config)
            self.mt5_service.initialize()
            self.mt5_service.select_symbols(["XAUUSD", "BTCUSD"])
            logger.info("✅ Service MT5 initialisé")
            
            # Service GPT
            self.gpt_service = GPTService(self.config)
            logger.info("✅ Service GPT initialisé")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des services: {e}")
            raise
    
    async def start(self):
        """Démarre le bot"""
        try:
            if not await self.initialize():
                return False
            
            self.is_running = True
            logger.info("🎯 Bot démarré, en attente de messages...")
            
            # Lancement en mode écoute
            await self.telegram_service.run()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Arrêt du bot demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur critique: {e}")
            raise TradingBotException(f"Erreur critique: {e}")
        finally:
            await self.cleanup()
    
    async def stop(self):
        """Arrête le bot proprement"""
        logger.info("🛑 Arrêt du bot en cours...")
        self.is_running = False
        await self.cleanup()
    
    async def cleanup(self):
        """Nettoie les ressources"""
        try:
            if self.mt5_service:
                self.mt5_service.shutdown()
            
            if self.telegram_service:
                await self.telegram_service.disconnect()
            
            logger.info("🧹 Nettoyage terminé")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
    def get_status(self) -> dict:
        """Retourne le statut du bot"""
        return {
            "running": self.is_running,
            "telegram_connected": self.telegram_service.client.is_connected() if self.telegram_service and self.telegram_service.client else False,
            "mt5_connected": self.mt5_service.is_connected if self.mt5_service else False,
            "channels_configured": len(self.telegram_service.channel_entities) if self.telegram_service else 0
        }

async def main():
    """Point d'entrée principal"""
    bot = TradingBot()
    
    try:
        await bot.start()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        return False
    
    return True

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erreur fatale dans main: {e}")
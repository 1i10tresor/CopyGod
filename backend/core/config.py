import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradingConfig:
    """Configuration centralisée pour le bot de trading"""
    
    # Telegram
    api_id: str
    api_hash: str
    
    # OpenAI
    gpt_key: str
    
    # MetaTrader 5
    mt5_login: str
    mt5_password: str
    mt5_server: str
    
    # Trading
    lot_size: float = 0.01
    expiration_minutes: int = 10
    
    # Canaux
    channel_ids: List[int] = None
    indo_channel_ids: List[int] = None
    kasper_id: int = -2259371711
    
    @classmethod
    def from_env(cls) -> 'TradingConfig':
        """Charge la configuration depuis les variables d'environnement"""
        load_dotenv()
        
        required_vars = ['api_id', 'api_hash', 'GPT_KEY', 'MT5_LOGIN', 'MT5_PSWRD', 'MT5_SERVEUR']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Variables d'environnement manquantes: {missing_vars}")
            raise ValueError(f"Variables d'environnement manquantes: {missing_vars}")
        
        return cls(
            api_id=os.getenv('api_id'),
            api_hash=os.getenv('api_hash'),
            gpt_key=os.getenv('GPT_KEY'),
            mt5_login=os.getenv('MT5_LOGIN'),
            mt5_password=os.getenv('MT5_PSWRD'),
            mt5_server=os.getenv('MT5_SERVEUR'),
            channel_ids=[-2259371711, -1770543299, -2507130648, -1441894073, -1951792433, -1428690627, -1260132661, -1626843631],
            indo_channel_ids=[2507130648, 1441894073, 1951792433, 1428690627, 1260132661, 1626843631]
        )
    
    def validate(self) -> bool:
        """Valide la configuration"""
        try:
            if not all([self.api_id, self.api_hash, self.gpt_key, self.mt5_login, self.mt5_password, self.mt5_server]):
                return False
            
            if self.lot_size <= 0 or self.expiration_minutes <= 0:
                return False
                
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la validation de la configuration: {e}")
            return False
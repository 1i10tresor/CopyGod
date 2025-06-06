import MetaTrader5 as mt5
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
import time
from ..core.config import TradingConfig
from ..core.exceptions import MT5ConnectionError, OrderValidationError

logger = logging.getLogger(__name__)

class MT5Service:
    """Service de gestion MetaTrader 5"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.is_connected = False
        
    def initialize(self, max_retries: int = 3) -> bool:
        """Initialise la connexion MT5"""
        for attempt in range(max_retries):
            try:
                if mt5.initialize(
                    login=int(self.config.mt5_login),
                    password=self.config.mt5_password,
                    server=self.config.mt5_server
                ):
                    self.is_connected = True
                    logger.info("Connexion à MetaTrader 5 réussie")
                    return True
                else:
                    logger.warning(f"Tentative {attempt + 1}/{max_retries} de connexion MT5 échouée")
                    if attempt == max_retries - 1:
                        raise MT5ConnectionError("Échec de l'initialisation après plusieurs tentatives")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation MT5 (tentative {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise MT5ConnectionError(f"Erreur d'initialisation: {e}")
                time.sleep(2)
                
        return False
    
    def select_symbols(self, symbols: List[str]) -> bool:
        """Sélectionne les symboles de trading"""
        if not self.is_connected:
            raise MT5ConnectionError("MT5 non connecté")
            
        for symbol in symbols:
            try:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Erreur lors de la sélection du symbole {symbol}")
                    return False
                else:
                    logger.info(f"Symbole {symbol} sélectionné avec succès")
            except Exception as e:
                logger.error(f"Exception lors de la sélection du symbole {symbol}: {e}")
                return False
                
        return True
    
    def get_tick_info(self, symbol: str) -> Optional[Any]:
        """Récupère les informations de tick pour un symbole"""
        if not self.is_connected:
            raise MT5ConnectionError("MT5 non connecté")
            
        try:
            tick_info = mt5.symbol_info_tick(symbol)
            if tick_info is None:
                logger.error(f"Impossible de récupérer les informations de tick pour {symbol}")
                return None
            return tick_info
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix pour {symbol}: {e}")
            return None
    
    def send_order(self, request: Dict[str, Any]) -> Optional[Any]:
        """Envoie un ordre de trading"""
        if not self.is_connected:
            raise MT5ConnectionError("MT5 non connecté")
            
        try:
            order = mt5.order_send(request)
            if order is None:
                logger.error(f"Échec de l'envoi de l'ordre. Erreur: {mt5.last_error()}")
                return None
            return order
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'ordre: {e}")
            return None
    
    def get_positions(self) -> Optional[List]:
        """Récupère les positions actuelles"""
        if not self.is_connected:
            raise MT5ConnectionError("MT5 non connecté")
            
        try:
            positions = mt5.positions_get()
            if positions is None:
                logger.error("Impossible de récupérer les positions actuelles")
                return None
            return list(positions)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des positions: {e}")
            return None
    
    def modify_position(self, position_id: int, sl: float, tp: float) -> Optional[Any]:
        """Modifie une position existante"""
        if not self.is_connected:
            raise MT5ConnectionError("MT5 non connecté")
            
        try:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position_id,
                "sl": float(sl),
                "tp": float(tp)
            }
            
            result = mt5.order_send(request)
            if result is None:
                logger.error(f"Échec de la modification de la position {position_id}: {mt5.last_error()}")
                return None
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la modification de la position {position_id}: {e}")
            return None
    
    def create_order_request(self, symbol: str, volume: float, order_type: int, 
                           price: float, sl: float, tp: float, magic: int, 
                           comment: str = "Order from Telegram Bot") -> Dict[str, Any]:
        """Crée une requête d'ordre"""
        try:
            expire_date = datetime.now() + timedelta(minutes=self.config.expiration_minutes)
            expiration_timestamp = int(time.mktime(expire_date.timetuple()))
            
            deviation = 1 if symbol == "XAUUSD" else 2500 if symbol == "BTCUSD" else 1
            
            return {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": float(price),
                "sl": float(sl),
                "tp": float(tp),
                "deviation": deviation,
                "magic": int(magic),
                "comment": comment,
                "type_time": mt5.ORDER_TIME_SPECIFIED,
                "expiration": expiration_timestamp,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création de la requête d'ordre: {e}")
            raise OrderValidationError(f"Erreur de création de requête: {e}")
    
    def shutdown(self):
        """Ferme la connexion MT5"""
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            logger.info("Connexion MT5 fermée")
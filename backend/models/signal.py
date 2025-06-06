from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OrderType(Enum):
    BUY = 0
    SELL = 1

class SignalType(Enum):
    KASPER = "kasper"
    INDO = "indo"
    MODIFICATION = "modification"

@dataclass
class TradingSignal:
    """Modèle de données pour un signal de trading"""
    
    symbol: str
    entry_price: float
    stop_loss: float
    take_profits: List[float]
    order_type: OrderType
    signal_type: SignalType
    channel_id: int
    message_id: int
    lot_size: float = 0.01
    
    def __post_init__(self):
        """Validation après initialisation"""
        self.validate()
    
    def validate(self) -> bool:
        """Valide la cohérence du signal"""
        try:
            # Validation des prix
            if self.entry_price <= 0 or self.stop_loss <= 0:
                raise ValueError("Les prix doivent être positifs")
            
            if not self.take_profits or any(tp <= 0 for tp in self.take_profits):
                raise ValueError("Les take profits doivent être positifs")
            
            # Validation de la logique BUY/SELL
            if self.order_type == OrderType.BUY:
                if self.stop_loss >= self.entry_price:
                    raise ValueError("Pour un BUY, le SL doit être inférieur à l'Entry")
                if any(tp <= self.entry_price for tp in self.take_profits):
                    raise ValueError("Pour un BUY, tous les TP doivent être supérieurs à l'Entry")
            
            elif self.order_type == OrderType.SELL:
                if self.stop_loss <= self.entry_price:
                    raise ValueError("Pour un SELL, le SL doit être supérieur à l'Entry")
                if any(tp >= self.entry_price for tp in self.take_profits):
                    raise ValueError("Pour un SELL, tous les TP doivent être inférieurs à l'Entry")
            
            # Validation du symbole
            if self.symbol not in ["XAUUSD", "BTCUSD"]:
                raise ValueError(f"Symbole non supporté: {self.symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur de validation du signal: {e}")
            raise
    
    @classmethod
    def from_gpt_response(cls, gpt_data: dict, channel_id: int, message_id: int, 
                         signal_type: SignalType) -> 'TradingSignal':
        """Crée un signal depuis une réponse GPT"""
        try:
            return cls(
                symbol=gpt_data["actif"],
                entry_price=float(gpt_data["Entry"]),
                stop_loss=float(gpt_data["SL"]),
                take_profits=[float(tp) for tp in gpt_data["TP"]],
                order_type=OrderType(gpt_data["sens"]),
                signal_type=signal_type,
                channel_id=channel_id,
                message_id=message_id
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création du signal depuis GPT: {e}")
            raise
    
    @classmethod
    def create_kasper_signal(cls, symbol: str, order_type: OrderType, price: float, 
                           channel_id: int, message_id: int) -> 'TradingSignal':
        """Crée un signal Kasper avec des paramètres prédéfinis"""
        try:
            if symbol == "XAUUSD":
                if order_type == OrderType.BUY:
                    tps = [price + 4, price + 8, price + 12]
                    sl = price - 4
                else:  # SELL
                    tps = [price - 4, price - 8, price - 12]
                    sl = price + 4
            elif symbol == "BTCUSD":
                if order_type == OrderType.BUY:
                    tps = [price + 400, price + 800, price + 1200]
                    sl = price - 400
                else:  # SELL
                    tps = [price - 400, price - 800, price - 1200]
                    sl = price + 400
            else:
                raise ValueError(f"Symbole non supporté pour Kasper: {symbol}")
            
            return cls(
                symbol=symbol,
                entry_price=price,
                stop_loss=sl,
                take_profits=tps,
                order_type=order_type,
                signal_type=SignalType.KASPER,
                channel_id=channel_id,
                message_id=message_id
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création du signal Kasper: {e}")
            raise

@dataclass
class PendingOrder:
    """Modèle pour les ordres en attente"""
    
    symbol: str
    message_id: int
    order_ids: List[int]
    order_type: OrderType
    pending: bool = True
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour la sérialisation"""
        return {
            "pending_order": self.pending,
            "symbol": self.symbol,
            "message_id": self.message_id,
            "order_ids": self.order_ids,
            "sens": self.order_type.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PendingOrder':
        """Crée depuis un dictionnaire"""
        return cls(
            symbol=data["symbol"],
            message_id=data["message_id"],
            order_ids=data["order_ids"],
            order_type=OrderType(data["sens"]),
            pending=data.get("pending_order", True)
        )
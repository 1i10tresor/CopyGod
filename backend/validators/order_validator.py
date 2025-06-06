from typing import Dict, Any
import logging
from ..core.exceptions import OrderValidationError

logger = logging.getLogger(__name__)

class OrderValidator:
    """Validateur d'ordres de trading"""
    
    @staticmethod
    def validate_order_request(request: Dict[str, Any], market_price: float) -> bool:
        """Valide une requête d'ordre avant envoi"""
        try:
            # Validation des champs requis
            required_fields = ["price", "symbol", "deviation", "sl", "tp", "type"]
            missing_fields = [field for field in required_fields if field not in request]
            if missing_fields:
                logger.error(f"Champs manquants dans la requête: {missing_fields}")
                return False
            
            # Conversion et validation des prix
            try:
                request_price = float(request["price"])
                sl_price = float(request["sl"])
                tp_price = float(request["tp"])
                market_price = float(market_price)
            except (ValueError, TypeError) as e:
                logger.error(f"Erreur de conversion des prix: {e}")
                return False
            
            if any(price <= 0 for price in [market_price, request_price, sl_price, tp_price]):
                logger.error("Tous les prix doivent être positifs")
                return False
            
            # Vérification de l'écart de prix
            price_diff_ratio = abs(request_price - market_price) / request_price
            if price_diff_ratio > 0.0035:
                logger.warning(f"Écart trop important entre le prix demandé : {request_price} $ et le prix du marché : {market_price} $")
                return False
            
            # Vérification des déviations par symbole
            symbol = request["symbol"]
            deviation = request["deviation"]
            
            if symbol == "XAUUSD" and deviation > 301:
                logger.warning("Déviation trop importante pour XAUUSD")
                return False
            elif symbol == "BTCUSD" and deviation > 2501:
                logger.warning("Déviation trop importante pour BTCUSD")
                return False
            
            # Vérification de la cohérence SL/TP selon le type d'ordre
            order_type = request["type"]
            
            if order_type == 0:  # BUY
                if sl_price > request_price:
                    logger.warning("SL supérieur à l'Entry pour un ordre BUY")
                    return False
                if tp_price < request_price:
                    logger.warning("TP inférieur à l'Entry pour un ordre BUY")
                    return False
            elif order_type == 1:  # SELL
                if sl_price < request_price:
                    logger.warning("SL inférieur à l'Entry pour un ordre SELL")
                    return False
                if tp_price > request_price:
                    logger.warning("TP supérieur à l'Entry pour un ordre SELL")
                    return False
            
            # Vérification des écarts SL et TP
            sl_diff = abs(request_price - sl_price)
            tp_diff = abs(request_price - tp_price)
            
            if sl_diff > 0.01 * request_price:
                logger.warning(f"Écart trop important entre l'Entry et le SL: {sl_diff} points")
                return False
            
            if tp_diff > 0.02 * request_price or tp_diff < 0.0008 * request_price:
                logger.warning(f"Écart inapproprié entre l'Entry et le TP : {tp_diff} points")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur dans la validation de l'ordre: {e}")
            raise OrderValidationError(f"Erreur de validation: {e}")
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Valide un symbole de trading"""
        return symbol in ["XAUUSD", "BTCUSD"]
    
    @staticmethod
    def validate_lot_size(lot_size: float) -> bool:
        """Valide la taille du lot"""
        return 0 < lot_size <= 100  # Limites raisonnables
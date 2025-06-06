"""Exceptions personnalisées pour le bot de trading"""

class TradingBotException(Exception):
    """Exception de base pour le bot de trading"""
    pass

class ConfigurationError(TradingBotException):
    """Erreur de configuration"""
    pass

class TelegramConnectionError(TradingBotException):
    """Erreur de connexion Telegram"""
    pass

class MT5ConnectionError(TradingBotException):
    """Erreur de connexion MetaTrader 5"""
    pass

class OrderValidationError(TradingBotException):
    """Erreur de validation d'ordre"""
    pass

class SignalParsingError(TradingBotException):
    """Erreur de parsing de signal"""
    pass

class GPTError(TradingBotException):
    """Erreur liée à GPT"""
    pass
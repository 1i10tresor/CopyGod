import MetaTrader5 as mt5
import os 
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time


load_dotenv()
mt5_login = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PSWRD")
mt5_server = os.getenv("MT5_SERVEUR")

# Date actuelle + 10 minutes
expire_date = datetime.now() + timedelta(minutes=10)

# Conversion en timestamp UNIX
expiration_timestamp = int(time.mktime(expire_date.timetuple()))



def send_order(symbol, sl, tp, sens):
    mt5.initialize(login=mt5_login, password=mt5_password, server=mt5_server)
    expire_date = datetime.now() + timedelta(minutes=10)
    expiration_timestamp = int(time.mktime(expire_date.timetuple()))
    price = mt5.symbol_info_tick(symbol).ask if sens == 0 else mt5.symbol_info_tick(symbol).bid
    lot_size = 0.01 
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if sens == 0 else mt5.ORDER_TYPE_SELL,  # 1 for buy, 0 for sell
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 1,
        "magic": 0, #plus tard le magic doit etre le numéro du canal
        "comment": "Order from Telegram CopyGod",
        "type_time": mt5.ORDER_TIME_SPECIFIED,
        "expiration": mt5.datetime(expiration_timestamp),  # Set expiration date
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    # Envoi de la requête d'ordre
    order = mt5.order_send(request)
    return order

print(expiration_timestamp, expire_date)

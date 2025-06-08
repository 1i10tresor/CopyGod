from telethon import TelegramClient
from dotenv import load_dotenv
import os
import asyncio
import re
from openai import AsyncOpenAI
from telethon import events
from telethon.tl.types import PeerChannel
import MetaTrader5 as mt5
import os 
from datetime import datetime, timedelta
import time
import ast
from kasper import *
import logging  # modified

# Configuration du logging  # modified
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)  # modified
logger = logging.getLogger(__name__)  # modified

load_dotenv()

# Validation des variables d'environnement  # modified
required_env_vars = ['api_id', 'api_hash', 'GPT_KEY', 'MT5_LOGIN', 'MT5_PSWRD', 'MT5_SERVEUR']  # modified
missing_vars = [var for var in required_env_vars if not os.getenv(var)]  # modified
if missing_vars:  # modified
    logger.error(f"Variables d'environnement manquantes: {missing_vars}")  # modified
    raise ValueError(f"Variables d'environnement manquantes: {missing_vars}")  # modified

api_id = os.getenv('api_id')  
api_hash = os.getenv('api_hash')  
gpt_key = os.getenv('GPT_KEY')

try:  # modified
    client_gpt = AsyncOpenAI(api_key=gpt_key)
except Exception as e:  # modified
    logger.error(f"Erreur lors de l'initialisation du client OpenAI: {e}")  # modified
    raise  # modified

try:  # modified
    client = TelegramClient('anon', api_id, api_hash)
except Exception as e:  # modified
    logger.error(f"Erreur lors de l'initialisation du client Telegram: {e}")  # modified
    raise  # modified

mt5_login = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PSWRD")
mt5_server = os.getenv("MT5_SERVEUR")

try:  # modified
    expire_date = datetime.now() + timedelta(minutes=10)
    expiration_timestamp = int(time.mktime(expire_date.timetuple()))
except Exception as e:  # modified
    logger.error(f"Erreur lors du calcul de la date d'expiration: {e}")  # modified
    expiration_timestamp = None  # modified

channel_ids = [-2259371711, -1770543299, -2507130648, -1441894073, -1951792433, -1428690627, -1260132661, -1626843631]
indo_channel_ids = [2507130648, 1441894073, 1951792433, 1428690627, 1260132661, 1626843631 ]
kasper_id = -2259371711


async def main():
    try:  # modified
        if not await client.start():
            logger.error("Échec de la connexion au client Telegram.")  # modified
            return
        logger.info("Connexion Telegram réussie.")  # modified
        
        channel_entities = []
        for channel_id in channel_ids:
            try:
                channel_entity = await client.get_entity(PeerChannel(channel_id))
                channel_entities.append(channel_entity)
                logger.info(f"Canal {channel_id} récupéré avec succès")  # modified
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du canal ID {channel_id}: {e}")  # modified
                continue  # modified
                
        if not channel_entities:
            logger.error("Aucun canal trouvé. Veuillez vérifier les IDs.")  # modified
            await client.disconnect()
            return
            
        # Validation de la connexion MT5  # modified
        max_retries = 3  # modified
        for attempt in range(max_retries):  # modified
            try:  # modified
                if mt5.initialize(login=int(mt5_login), password=mt5_password, server=mt5_server):
                    logger.info("Connexion à MetaTrader 5 réussie.")  # modified
                    break  # modified
                else:  # modified
                    logger.warning(f"Tentative {attempt + 1}/{max_retries} de connexion MT5 échouée")  # modified
                    if attempt == max_retries - 1:  # modified
                        logger.error("Échec de l'initialisation de MetaTrader 5 après plusieurs tentatives.")  # modified
                        mt5.shutdown()
                        return
                    await asyncio.sleep(2)  # modified
            except Exception as e:  # modified
                logger.error(f"Erreur lors de l'initialisation MT5 (tentative {attempt + 1}): {e}")  # modified
                if attempt == max_retries - 1:  # modified
                    return
                await asyncio.sleep(2)  # modified
                
        # Validation des symboles  # modified
        symbols_to_select = ["XAUUSD", "BTCUSD"]  # modified
        for symbol in symbols_to_select:  # modified
            try:  # modified
                if not mt5.symbol_select(symbol, True):  # modified
                    logger.error(f"Erreur lors de la sélection du symbole {symbol}")  # modified
                    return
                else:  # modified
                    logger.info(f"Symbole {symbol} sélectionné avec succès")  # modified
            except Exception as e:  # modified
                logger.error(f"Exception lors de la sélection du symbole {symbol}: {e}")  # modified
                return
                
        @client.on(events.NewMessage(chats=channel_entities))
        async def handle_new_message(event):
            try:  # modified
                message = event.message
                entity = await client.get_entity(-event.chat_id)
                if abs(entity.id) == abs(kasper_id):
                    await signal_or_modify(message)
                else:
                    logger.warning(f"Message reçu d'un canal non autorisé: {entity.id}")  # modified
            except Exception as e:  # modified
                logger.error(f"Erreur lors du traitement du message: {e}")  # modified

        logger.info("Bot démarré, en attente de messages...")  # modified
        await client.run_until_disconnected()
        
    except KeyboardInterrupt:  # modified
        logger.info("Arrêt du bot demandé par l'utilisateur")  # modified
    except Exception as e:  # modified
        logger.error(f"Erreur critique dans la fonction main: {e}")  # modified
    finally:  # modified
        try:  # modified
            if mt5.initialize():  # modified
                mt5.shutdown()
                logger.info("Connexion MT5 fermée")  # modified
            if client.is_connected():  # modified
                await client.disconnect()
                logger.info("Connexion Telegram fermée")  # modified
        except Exception as e:  # modified
            logger.error(f"Erreur lors de la fermeture des connexions: {e}")  # modified


if __name__ == '__main__':   
    try:  # modified
        asyncio.run(main())
    except Exception as e:  # modified
        logger.error(f"Erreur fatale: {e}")  # modified
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
load_dotenv()
api_id = os.getenv('api_id')  
api_hash = os.getenv('api_hash')  
gpt_key = os.getenv('GPT_KEY')
client_gpt = AsyncOpenAI(api_key=gpt_key)
client = TelegramClient('anon', api_id, api_hash)
mt5_login = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PSWRD")
mt5_server = os.getenv("MT5_SERVEUR")
expire_date = datetime.now() + timedelta(minutes=10)
expiration_timestamp = int(time.mktime(expire_date.timetuple()))
channel_ids = [-2259371711, -1770543299, -2507130648, -1441894073, -1951792433, -1428690627, -1260132661, -1626843631]
indo_channel_ids = [2507130648, 1441894073, 1951792433, 1428690627, 1260132661, 1626843631 ]
kasper_id = -2259371711


async def main():
    if not await client.start() :
        print("Échec de la connexion au client Telegram.")
        return
    print("Connexion réussie.")
    channel_entities = []
    for channel_id in channel_ids:
        try:
            channel_entity = await client.get_entity(PeerChannel(channel_id))
            channel_entities.append(channel_entity)
        except Exception as e:
            print(f"Erreur lors de la récupération du canal ID {channel_id}: {e}")
    if not channel_entities:
        print("Aucun canal trouvé. Veuillez vérifier les IDs.")
        await client.disconnect()
        return
    if not mt5.initialize(login=int(mt5_login), password=mt5_password, server=mt5_server) :
        print("Échec de l'initialisation de MetaTrader 5.")
        mt5.shutdown()
        return
    print("Connexion à MetaTrader 5 réussie.")
    if mt5.symbol_select("XAUUSD", True) and mt5.symbol_select("BTCUSD", True) :
        print("Symboles XAUUSD et BTCUSD sélectionnés avec succès.")
    else:
        print("Erreur lors de la sélection des symboles XAUUSD et BTCUSD.")
        return
    @client.on(events.NewMessage(chats=channel_entities))
    async def handle_new_message(event):
        message = event.message
        entity = await client.get_entity(-event.chat_id)
        if abs(entity.id) == abs(kasper_id):
            return await signal_or_modify(message)
        else:
            print("erreur, le message n'est pas de Kasper")

    await client.run_until_disconnected()


if __name__ == '__main__':   
    asyncio.run(main())

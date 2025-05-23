from telethon.sync import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')
channel_id = 1264473344  # ID positif
session_name = 'anon'

with TelegramClient(session_name, api_id, api_hash) as client:
    try:
        channel = client.get_entity(int(f"-100{channel_id}"))
        messages = client.get_messages(channel, limit=20)  # On prend plus de messages pour le contexte
        
        print(f"\n📊 Derniers messages du canal [Le Trading Gratuit 🆓]:")

        for msg in messages:
            # Affichage du message principal
            print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"🗨️ Nouveau message (ID: {msg.id})")
            print(f"🕒 {msg.date}")
            print(f"👤 Auteur: {msg.sender_id if hasattr(msg, 'sender_id') else 'Système'}")
            print(f"📝 Contenu: {msg.text or '<message média ou vide>'}")
            
            # Si c'est une réponse à un autre message
            if msg.reply_to:
                try:
                    replied_msg = client.get_messages(channel, ids=msg.reply_to.reply_to_msg_id)
                    print(f"\n↪️ Réponse à (ID: {replied_msg.id}):")
                    print(f"🕒 {replied_msg.date}")
                    print(f"👤 Auteur original: {replied_msg.sender_id if hasattr(replied_msg, 'sender_id') else 'Système'}")
                    print(f"💬 Message original: {replied_msg.text or '<message média ou vide>'}")
                    
                except Exception as e:
                    print(f"\n⚠️ Impossible de récupérer le message original: {e}")

    except Exception as e:
        print(f"❌ Erreur majeure: {e}")
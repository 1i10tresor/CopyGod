from flask import Flask, jsonify
from flask_cors import CORS
from telethon.sync import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)

load_dotenv()
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')
session_name = 'anon'

@app.route('/channels')
def get_channels():
    with TelegramClient(session_name, api_id, api_hash) as client:
        result = client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=100,
            hash=0
        ))
        
        channels = []
        for chat in result.chats:
            if isinstance(chat, (Channel, Chat)):
                channels.append({
                    'id': chat.id,
                    'title': chat.title,
                    'type': "Canal" if isinstance(chat, Channel) and chat.megagroup is False else "Groupe"
                })
        
        return jsonify(channels)

@app.route('/messages/<int:channel_id>')
def get_messages(channel_id):
    with TelegramClient(session_name, api_id, api_hash) as client:
        try:
            channel = client.get_entity(int(f"-100{channel_id}"))
            messages = client.get_messages(channel, limit=10)
            
            messages_list = []
            for msg in messages:
                message_data = {
                    'id': msg.id,
                    'date': msg.date.isoformat(),
                    'sender_id': msg.sender_id if hasattr(msg, 'sender_id') else 'Système',
                    'text': msg.text or '<message média ou vide>'
                }
                
                if msg.reply_to:
                    try:
                        replied_msg = client.get_messages(channel, ids=msg.reply_to.reply_to_msg_id)
                        message_data['reply_to'] = {
                            'id': replied_msg.id,
                            'date': replied_msg.date.isoformat(),
                            'sender_id': replied_msg.sender_id if hasattr(replied_msg, 'sender_id') else 'Système',
                            'text': replied_msg.text or '<message média ou vide>'
                        }
                    except Exception:
                        message_data['reply_to'] = None
                
                messages_list.append(message_data)
            
            return jsonify(messages_list)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
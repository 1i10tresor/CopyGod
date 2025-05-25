from flask import Flask, jsonify, request
from flask_cors import CORS
from telethon.sync import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from dotenv import load_dotenv
import os
import re
import json
import time
from datetime import datetime, timezone
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')
session_name = 'anon'
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Trading constants
LOT_SIZE = 0.01
POSITIONS_PER_TRADE = 3
ALLOWED_PAIRS = ['XAUUSD', 'BTCUSD', 'GOLD', 'XAU', 'BTC']
MAX_VOLATILITY = 0.003  # 0.3%

class TradingBot:
    def __init__(self):
        self.positions = {}
        self.error_count = {}
        self.last_trade_time = None
        self.market_paused = False
        
    def check_market_hours(self):
        now = datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute
        return not (hour == 23 and minute >= 50) and not (hour == 0 and minute <= 10)
    
    def check_volatility(self, symbol):
        # TODO: Implement ATR calculation
        return True  # Placeholder
        
    def validate_trade(self, symbol, direction, price):
        if self.market_paused:
            logger.warning("Trading is currently paused")
            return False
            
        if not self.check_market_hours():
            logger.warning("Outside trading hours")
            return False
            
        normalized_symbol = self.normalize_symbol(symbol)
        if normalized_symbol not in ALLOWED_PAIRS:
            logger.warning(f"Invalid symbol: {symbol}")
            return False
            
        if not self.check_volatility(normalized_symbol):
            logger.warning(f"High volatility detected for {symbol}")
            return False
            
        return True
        
    def normalize_symbol(self, symbol):
        if symbol in ['GOLD', 'XAU']:
            return 'XAUUSD'
        if symbol in ['BTC']:
            return 'BTCUSD'
        return symbol
        
    async def process_phase1(self, message):
        try:
            # Parse trade signal
            pattern = r"(BUY|SELL)\s+(XAUUSD|BTCUSD|GOLD|XAU|BTC)\s+NOW"
            match = re.match(pattern, message.upper())
            
            if not match:
                return None
                
            direction, symbol = match.groups()
            # TODO: Get current price from MT5
            current_price = 1000.0  # Placeholder
            
            if not self.validate_trade(symbol, direction, current_price):
                return None
                
            # Calculate levels
            base_points = 6
            sl = current_price - base_points if direction == 'BUY' else current_price + base_points
            tps = [current_price + p if direction == 'BUY' else current_price - p 
                   for p in [6, 9, 12]]
            
            # Open positions
            timestamp = int(time.time())
            positions = []
            
            for i in range(POSITIONS_PER_TRADE):
                order_tag = f"{symbol}_{timestamp}_{i+1}"
                position = {
                    'symbol': symbol,
                    'direction': direction,
                    'volume': LOT_SIZE,
                    'entry_price': current_price,
                    'sl': sl,
                    'tp': tps[i],
                    'tag': order_tag,
                    'status': 'open'
                }
                positions.append(position)
                self.positions[order_tag] = position
            
            logger.info(f"Opened {len(positions)} positions for {symbol}")
            return positions
            
        except Exception as e:
            logger.error(f"Error in phase 1: {str(e)}")
            self.record_error('phase1')
            return None
            
    async def process_phase2(self, message):
        try:
            # Call DeepSeek API
            levels = await self.parse_levels_deepseek(message)
            if not levels:
                # Fallback to regex
                levels = self.parse_levels_regex(message)
                
            if not levels:
                logger.error("Failed to parse levels")
                return False
                
            # Validate levels
            if not self.validate_levels(levels):
                logger.warning("Invalid levels")
                return False
                
            # Update positions
            for tag, position in self.positions.items():
                if position['status'] == 'open':
                    position['sl'] = levels['SL']
                    if 'TP1' in levels and position['tp'] == position['entry_price'] + 6:
                        position['tp'] = levels['TP1']
                    elif 'TP2' in levels and position['tp'] == position['entry_price'] + 9:
                        position['tp'] = levels['TP2']
                    elif 'TP3' in levels and position['tp'] == position['entry_price'] + 12:
                        position['tp'] = levels['TP3']
                        
            logger.info("Successfully updated positions with new levels")
            return True
            
        except Exception as e:
            logger.error(f"Error in phase 2: {str(e)}")
            self.record_error('phase2')
            return False
            
    async def parse_levels_deepseek(self, message):
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [{
                        "role": "user",
                        "content": f"Extract SL, TP1, TP2, TP3 from: {message}. Reply ONLY with JSON format: {{\"SL\":x,\"TP1\":y,\"TP2\":z,\"TP3\":w}}"
                    }]
                }
            )
            
            if response.status_code == 200:
                return json.loads(response.json()['choices'][0]['message']['content'])
            return None
            
        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            return None
            
    def parse_levels_regex(self, message):
        try:
            sl_match = re.search(r"SL\s+([\d.]+)", message)
            tp_matches = re.finditer(r"TP\d?\s+([\d.]+)", message)
            
            if not sl_match:
                return None
                
            levels = {"SL": float(sl_match.group(1))}
            for i, tp_match in enumerate(tp_matches, 1):
                levels[f"TP{i}"] = float(tp_match.group(1))
                
            return levels
            
        except Exception:
            return None
            
    def validate_levels(self, levels):
        if 'SL' not in levels:
            return False
            
        prev_level = levels['SL']
        for i in range(1, 4):
            tp_key = f"TP{i}"
            if tp_key not in levels:
                continue
            if levels[tp_key] <= prev_level:
                return False
            prev_level = levels[tp_key]
            
        return True
        
    def record_error(self, error_type):
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        if self.error_count[error_type] >= 3:
            self.pause_trading()
            # TODO: Send SMS alert
            
    def pause_trading(self, duration_minutes=15):
        self.market_paused = True
        # TODO: Implement timer to unpause

# Initialize trading bot
trading_bot = TradingBot()

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
                
                # Process trading signals
                if msg.text:
                    if re.match(r"(BUY|SELL)\s+(XAUUSD|BTCUSD|GOLD|XAU|BTC)\s+NOW", msg.text.upper()):
                        trading_bot.process_phase1(msg.text)
                    elif re.match(r"SL\s+[\d.]+", msg.text.upper()):
                        trading_bot.process_phase2(msg.text)
                
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

@app.route('/trading/status')
def get_trading_status():
    return jsonify({
        'positions': list(trading_bot.positions.values()),
        'market_paused': trading_bot.market_paused,
        'error_count': trading_bot.error_count
    })

if __name__ == '__main__':
    app.run(debug=True)
import dotenv from 'dotenv';
import TelegramBot from 'node-telegram-bot-api';
import { setupTrading } from './trading.js';
import { setupMonitoring } from './monitoring.js';
import { logger } from './utils/logger.js';

dotenv.config();

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN, { polling: true });
const ALLOWED_CHANNELS = process.env.ALLOWED_CHANNELS.split(',');

// Trading setup
const trading = setupTrading(bot);

// Monitoring setup
const monitoring = setupMonitoring();

// Message handler
bot.on('message', async (msg) => {
  try {
    if (!ALLOWED_CHANNELS.includes(msg.chat.id.toString())) {
      return;
    }

    const messageText = msg.text.toUpperCase();
    
    // Phase 1: Initial trade trigger
    if (messageText.match(/(BUY|SELL)\s+(XAUUSD|BTCUSD|GOLD|XAU|BTC)\s+NOW/)) {
      await trading.handlePhase1(messageText, msg.date);
    }
    
    // Phase 2: SL/TP adjustment
    else if (messageText.match(/SL\s+\d+(\.\d+)?\s+TP/)) {
      await trading.handlePhase2(messageText, msg.date);
    }
  } catch (error) {
    logger.error('Error processing message:', error);
    monitoring.recordError('message_processing', error);
  }
});

logger.info('Trading bot started successfully');
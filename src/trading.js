import { MT5 } from './connectors/mt5.js';
import { DeepSeek } from './connectors/deepseek.js';
import { logger } from './utils/logger.js';
import { validateTrade, checkVolatility } from './utils/validators.js';

export function setupTrading(bot) {
  const mt5 = new MT5();
  const deepseek = new DeepSeek();
  
  const LOT_SIZE = 0.01;
  const POSITIONS_PER_TRADE = 3;
  
  async function handlePhase1(message, timestamp) {
    const { direction, symbol, price } = parseTradeMessage(message);
    
    // Pre-trade checks
    if (!validateTrade(symbol, price) || !checkVolatility(symbol)) {
      logger.warn('Pre-trade validation failed');
      return;
    }
    
    // Calculate SL/TP levels
    const basePoints = 6;
    const sl = direction === 'BUY' ? price - basePoints : price + basePoints;
    const tps = direction === 'BUY' 
      ? [price + 6, price + 9, price + 12]
      : [price - 6, price - 9, price - 12];
    
    // Open positions
    for (let i = 0; i < POSITIONS_PER_TRADE; i++) {
      const orderTag = `${symbol}_${timestamp}_${i + 1}`;
      await mt5.openPosition({
        symbol,
        type: direction,
        volume: LOT_SIZE,
        sl,
        tp: tps[i],
        tag: orderTag
      });
    }
  }
  
  async function handlePhase2(message, timestamp) {
    try {
      const levels = await deepseek.parseLevels(message);
      if (!validateLevels(levels)) {
        throw new Error('Invalid SL/TP levels');
      }
      
      const openPositions = await mt5.getOpenPositions();
      for (const position of openPositions) {
        await updatePosition(position, levels);
      }
    } catch (error) {
      logger.error('Phase 2 error:', error);
      // Implement fallback strategy
    }
  }
  
  return {
    handlePhase1,
    handlePhase2
  };
}
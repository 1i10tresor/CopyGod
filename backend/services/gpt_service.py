from openai import AsyncOpenAI
from typing import Optional, Dict, Any
import logging
import re
import ast
from ..core.config import TradingConfig
from ..core.exceptions import GPTError, SignalParsingError

logger = logging.getLogger(__name__)

class GPTService:
    """Service de gestion des interactions avec GPT"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        try:
            self.client = AsyncOpenAI(api_key=config.gpt_key)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client OpenAI: {e}")
            raise GPTError(f"Erreur d'initialisation OpenAI: {e}")
    
    async def analyze_signal(self, message_text: str, signal_type: str = "standard") -> Optional[Dict[str, Any]]:
        """Analyse un signal de trading avec GPT"""
        try:
            prompt = self._get_prompt(message_text, signal_type)
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                timeout=30
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à GPT-4: {e}")
            raise GPTError(f"Erreur GPT: {e}")
    
    def _get_prompt(self, message_text: str, signal_type: str) -> str:
        """Génère le prompt selon le type de signal"""
        base_prompt = f"""
        Tu es un expert en analyse de signaux de trading MetaTrader 5.

        Analyse le message Telegram suivant et, si c'est un signal de trading valide, extraits-en les composants :

        \"\"\"{message_text}\"\"\"

        Règles strictes :
        1. Le message doit contenir :
        - Un prix d'entrée (Entry)
        - Un Stop Loss (SL)
        - Au moins un Take Profit (TP)
        - Un symbole d'actif (actif)

        2. Validations :
        - Pour un BUY :
            - SL doit être inférieur à Entry
            - Chaque TP doit être supérieur à Entry
        - Pour un SELL :
            - SL doit être supérieur à Entry
            - Chaque TP doit être inférieur à Entry
        - Aucun champ ne doit être inventé. Si une valeur est absente ou ambigüe, retourne `false`.

        Réponse STRICTE :
        - Si les conditions sont remplies, retourne UNIQUEMENT un dictionnaire avec ce format :
        {{
        "sens": 0|1,             // 0 = BUY, 1 = SELL
        "actif": "SYMBOLE",      // ex: XAUUSD ou BTCUSD. L'actif doit être au format paire de trading completement en majuscules => pour l'or = XAUUSD, pour le bitcoin = BTCUSD
        "SL": "prix",            // string
        "Entry": "prix",         // string
        "TP": ["tp1", "tp2"]     // Liste de 1 à 4 TP (strings)
        }}

        - Sinon, retourne simplement : false

        Pas de commentaires, pas de texte additionnel. Seulement le dictionnaire ou false.
        """
        
        if signal_type == "modification":
            base_prompt += "\n\nNote: Ce message est une modification d'un signal existant."
            
        return base_prompt
    
    def _parse_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse la réponse de GPT"""
        try:
            match = re.search(r'\{.*?\}', response_content, re.DOTALL)
            if not match:
                return None
                
            response_text = ast.literal_eval(match.group(0))
            
            # Validation de la structure
            if not isinstance(response_text, dict):
                return None
                
            required_keys = ["sens", "SL", "Entry", "actif"]
            if not all(key in response_text for key in required_keys):
                return None
                
            # Nettoyage des espaces
            cleaned_response = {
                k: [tp.replace(" ", "") for tp in v] if isinstance(v, list)
                else v.replace(" ", "") if isinstance(v, str)
                else v
                for k, v in response_text.items()
            }
            
            return cleaned_response
            
        except (ValueError, SyntaxError, AttributeError) as e:
            logger.error(f"Erreur lors du parsing de la réponse GPT-4: {e}")
            raise SignalParsingError(f"Erreur de parsing: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors du traitement de la réponse GPT-4: {e}")
            raise SignalParsingError(f"Erreur inattendue: {e}")
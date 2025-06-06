# Bot de Trading - Architecture POO

## Vue d'ensemble

Cette version refactorisée du bot de trading utilise une architecture orientée objet pour améliorer la maintenabilité, la testabilité et la séparation des responsabilités.

## Architecture

### Structure des dossiers

```
backend/
├── core/
│   ├── config.py          # Configuration centralisée
│   └── exceptions.py      # Exceptions personnalisées
├── services/
│   ├── telegram_service.py # Gestion Telegram
│   ├── mt5_service.py     # Gestion MetaTrader 5
│   └── gpt_service.py     # Gestion GPT/OpenAI
├── models/
│   └── signal.py          # Modèles de données
├── validators/
│   └── order_validator.py # Validation des ordres
├── handlers/
│   └── message_handler.py # Gestionnaire de messages
├── processors/
│   ├── kasper_processor.py # Traitement signaux Kasper
│   └── indo_processor.py  # Traitement signaux Indo
└── main_oop.py           # Point d'entrée principal
```

### Composants principaux

#### 1. **TradingConfig** (`core/config.py`)
- Configuration centralisée chargée depuis les variables d'environnement
- Validation automatique des paramètres
- Valeurs par défaut pour les paramètres de trading

#### 2. **Services** (`services/`)
- **TelegramService**: Gestion des connexions et messages Telegram
- **MT5Service**: Interface avec MetaTrader 5
- **GPTService**: Interactions avec l'API OpenAI

#### 3. **Modèles** (`models/`)
- **TradingSignal**: Représentation d'un signal de trading
- **PendingOrder**: Gestion des ordres en attente
- **OrderType/SignalType**: Énumérations pour les types

#### 4. **Processeurs** (`processors/`)
- **KasperProcessor**: Logique spécifique aux signaux Kasper
- **IndoProcessor**: Logique spécifique aux signaux Indo

#### 5. **Validateurs** (`validators/`)
- **OrderValidator**: Validation éthique et technique des ordres

## Avantages de cette architecture

### ✅ **Séparation des responsabilités**
- Chaque classe a une responsabilité unique et bien définie
- Services découplés et réutilisables

### ✅ **Gestion d'erreurs améliorée**
- Exceptions personnalisées pour chaque type d'erreur
- Propagation contrôlée des erreurs

### ✅ **Testabilité**
- Chaque composant peut être testé indépendamment
- Injection de dépendances facilitée

### ✅ **Maintenabilité**
- Code organisé et facile à comprendre
- Modifications localisées sans impact sur le reste

### ✅ **Extensibilité**
- Ajout facile de nouveaux types de signaux
- Architecture modulaire

## Utilisation

### Démarrage du bot

```python
from main_oop import TradingBot

# Création et démarrage du bot
bot = TradingBot()
await bot.start()
```

### Configuration

Créez un fichier `.env` avec vos paramètres :

```env
api_id=your_telegram_api_id
api_hash=your_telegram_api_hash
GPT_KEY=your_openai_api_key
MT5_LOGIN=your_mt5_login
MT5_PSWRD=your_mt5_password
MT5_SERVEUR=your_mt5_server
```

### Ajout d'un nouveau type de signal

1. Créer un nouveau processeur dans `processors/`
2. Hériter de la classe de base ou implémenter l'interface
3. Enregistrer le processeur dans `MessageHandler`

```python
class NewSignalProcessor:
    def __init__(self, config, gpt_service, mt5_service):
        self.config = config
        self.gpt_service = gpt_service
        self.mt5_service = mt5_service
    
    async def process_message(self, message, entity):
        # Logique de traitement
        pass
```

## Comparaison avec l'ancienne version

| Aspect | Ancienne version | Nouvelle version POO |
|--------|------------------|---------------------|
| **Structure** | Fonctions globales | Classes et services |
| **Configuration** | Variables globales | Classe TradingConfig |
| **Gestion d'erreurs** | Try/catch dispersés | Exceptions personnalisées |
| **Testabilité** | Difficile | Facile avec mocks |
| **Maintenance** | Complexe | Modulaire |
| **Extensibilité** | Limitée | Excellente |

## Tests

Pour tester un composant :

```python
import pytest
from unittest.mock import Mock
from services.mt5_service import MT5Service

def test_mt5_service():
    config = Mock()
    service = MT5Service(config)
    # Tests...
```

## Logging

Le système de logging est configuré pour :
- Fichier de log : `trading_bot_oop.log`
- Console avec formatage
- Niveaux appropriés par composant

## Migration

Pour migrer de l'ancienne version :
1. Gardez vos fichiers de configuration (`.env`)
2. Utilisez `main_oop.py` au lieu de `app.py`
3. Les fonctionnalités restent identiques

Cette architecture POO offre une base solide pour l'évolution future du bot tout en maintenant toutes les fonctionnalités existantes.
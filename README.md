# Telegram Channel Viewer

A Vue.js application that allows viewing messages from Telegram channels using a Python/Flask backend.

## Setup

### Backend
1. Install Python dependencies:
```bash
pip install flask flask-cors python-dotenv telethon
```

2. Create a `.env` file in the backend directory with your Telegram API credentials:
```
api_id=your_api_id
api_hash=your_api_hash
```

3. Run the Flask server:
```bash
python app.py
```

### Frontend
1. Install dependencies:
```bash
cd copietrading
npm install
```

2. Run the development server:
```bash
npm run dev
```

## Features
- View available Telegram channels
- Display last 10 messages from selected channel
- Show message replies and threading
- Real-time updates

async def est_order(canale, message):
    canal = await client.get_entity(-canale)
    if message.text:
        has_sl = re.search(r"(?i)sl|stop\s*loss", message.text)
        has_tp = re.search(r"(?i)tp|take\s*profit", message.text)
        if has_sl and has_tp:
            print(f"Message ID: {message.id}, Date: {message.date}", "canal: ", canal.id, canal.title)
            print(f"Ordre trouvé")
            prompt = f"""
                Tu es un expert en analyse de signaux de trading MetaTrader 5.

                Analyse le message Telegram suivant et, si c'est un signal de trading valide, extraits-en les composants :

                \"\"\"{message.text}\"\"\"

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
            print("Envoi du prompt à GPT-4...")        
            response = await client_gpt.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "user", "content": prompt}])
            match = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL)
            response_text = ast.literal_eval(match.group(0)) if match else None
            print(response_text)
            def_order(response_text, canal)
            print("-" * 40)
        else:
            print(f"Message ID: {message.id}, Date: {message.date}", "canal: ", canal.id, canal.title)
            print("Pas un ordre de trading.")
            print("-" * 40)
    else :
        print(f"Message ID: {message.id}, Date: {message.date}", "canal: ", canal.id, canal.title)
        print("Message vide ou non textuel.")
        print("-" * 40)




def def_order(response_text_gpt, canal):
    print("Signal bien reçus par def_order, traitement en cours...")
    if response_text_gpt is None:
        print("Aucun signal de trading valide trouvé dans le message par chatgpt, None retourné.")
        return
    response_text =   {
        k: [tp.replace(" ", "") for tp in v] if isinstance(v, list)
        else v.replace(" ", "") if isinstance(v, str)
        else v
        for k, v in response_text_gpt.items()}
    print(f"Le signal du canal {canal.id}, est dans la liste des canaux indo : {canal.id in indo_channel_ids}")
    if canal.id in indo_channel_ids:
        sens = response_text["sens"]
        sl = response_text["SL"]
        tp = float(response_text["Entry"]) + float(float(response_text["Entry"])-float(response_text["SL"]))
        actif = response_text["actif"]
        entry = response_text["Entry"]
        send_order_indo(actif, sl, tp, sens, canal.id, entry)
    else:
        print(f"Le canal {canal.id} n'est pas dans la liste des canaux indo, ordre non envoyé.")
        print("Vérifiez si le canal est autorisé à envoyer des ordres.")
        return

def send_order_indo(symbol, sl, tp, sens, canal, entry):
    
    # gold = mt5.symbol_select("XAUUSD", True)
    # btc = mt5.symbol_select("BTCUSD", True)
    expire_date = datetime.now() + timedelta(minutes=10)
    expiration_timestamp = int(time.mktime(expire_date.timetuple()))
    price = mt5.symbol_info_tick(symbol).ask if sens == 0 else mt5.symbol_info_tick(symbol).bid
    lot_size = 0.01 
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot_size),
        "type": mt5.ORDER_TYPE_BUY if sens == 0 else mt5.ORDER_TYPE_SELL,  # 1 for buy, 0 for sell
        "price": float(entry),
        "sl": float(sl),
        "tp": float(tp), 
        "deviation": 1 if symbol == "XAUUSD"  else 2500 if symbol == "BTCUSD" else 1, 
        "magic": int(canal), 
        "comment": "Order from Telegram CopyGod",
        "type_time": mt5.ORDER_TIME_SPECIFIED,
        "expiration": expiration_timestamp,  
        "type_filling": mt5.ORDER_FILLING_FOK,}
    if commissions_ethyque_indo(request, price):
        order = mt5.order_send(request)
    else:
        print("❌ Commission non éthique détectée, ordre non envoyé.")
        return
    if order is None:
        print(f"Échec de l'envoi de l'ordre pour {symbol}. Erreur: {mt5.last_error()}")
    else:
        if order and order.retcode == mt5.TRADE_RETCODE_DONE:
            print("✅ Ordre passé avec succès.")
            print("Ticket:", order.order)
        else:
            print("❌ Échec de l'envoi de l'ordre.")
            if order:
                print("Code erreur :", order.retcode)
                print("Description :", order.comment)
            else:
                print("Erreur : Aucun résultat retourné.")


def commissions_ethyque_indo(request, price):
    if abs(request["price"]-price)/request["price"] > 0.0035:
        print(f"Ecart trop important entre le prix demandé : {request['price']} $ et le prix du marché : {price} $.")
        return False
    elif request["symbol"] == "XAUUSD" and request["deviation"] > 301:
        print("déviation trop importante pour XAUUSD.")
        return False
    elif request["symbol"] == "BTCUSD" and request["deviation"] > 2501:
        print("déviation trop importante pour BTCUSD.")
        return False
    elif request["sl"]> request["price"] and request["type"] == 0:
        print("SL inférieur à l'Entry pour un ordre BUY.")
        return False                
    elif request["sl"]< request["price"] and request["type"] == 1:
        print("SL supérieur à l'Entry pour un ordre SELL.")
        return False
    elif request["tp"] < request["price"] and request["type"] == 0:
        print("TP inférieur à l'Entry pour un ordre BUY.")
        return False
    elif request["tp"] > request["price"] and request["type"] == 1:
        print("TP supérieur à l'Entry pour un ordre SELL.")
        return False
    elif abs(request["price"]-request["sl"]) > 0.01* request["price"] :
        print(f"Ecart trop important entre l'Entry et le SL.{abs(request['price']-request['sl'])} points")
        return False
    elif abs(request["price"]-request["tp"]) > 0.02* request["price"] or abs(request["price"]-request["tp"]) < 0.0008* request["price"]:
        print(f"Ecart trop important entre l'Entry et le TP : {abs(request['price']-request['tp'])} points")
        return False
    else:
        return True



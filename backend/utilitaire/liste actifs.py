import MetaTrader5 as mt5

def main():
    # Initialize the MetaTrader 5 connection
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
        return

    # Get the account information
    account_info = mt5.account_info()
    if account_info is None:
        print("Failed to get account info")
        mt5.shutdown()
        return

    # Print the account information
    print(f"Account Number: {account_info.login}")
    print(f"Balance: {account_info.balance}")
    print(f"Equity: {account_info.equity}")

    symbols = mt5.symbols_get()
    gold = mt5.symbol_select("XAUUSD", True)
    btc = mt5.symbol_select("BTCUSD", True)
    print("Symbols selected:", gold, btc)

    # Shutdown the MetaTrader 5 connection
    mt5.shutdown()

if __name__ == "__main__":
    main()
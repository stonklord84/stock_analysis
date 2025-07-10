import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sqlite3


popular_symbols = ["AAPL","MSFT","NVDA","GOOGL","AMZN","TSLA","META","BRK.B","JPM","V"]

def analyze_stock(symbol):
    # Open the database
    conn = sqlite3.connect("data/stock_data.db")
    cursor = conn.cursor()

    # Check if the table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (symbol,)
    )
    if cursor.fetchone():
        print('hi? stage 1')
        # Check the latest date
        print('yes?')
        query = f"SELECT MAX(Date) FROM '{symbol}'" 
        cursor.execute(query)
        print('yes.......')
        latest_date = cursor.fetchone()[0]
        print(latest_date, 'latest_date')

        if latest_date:
            print('hi? stage 2')
            latest_date = pd.to_datetime(latest_date)
            today = pd.Timestamp.today().normalize()

            # If the latest date is today or yesterday, use cached data
            if latest_date >= today - pd.Timedelta(days=1):
                print('fucking hell, stage 3?')
                print(f"Loading {symbol} from DB.")
                data = pd.read_sql(f"SELECT * FROM '{symbol}'", conn, parse_dates=["Date"])
                print(data.columns, 'still have date?')  # Debug: confirm you still have 'Date'
                data.set_index("Date", inplace=True)

                conn.close()
                print(f"FINISHED analyzing {symbol}")
                return generate_chart_and_signal(symbol, data)

    # Else: download fresh data
    print(f"Downloading fresh data for {symbol}...")
    data = yf.download(symbol, period="6mo", interval="1d")

    if data.empty or len(data) < 20:
        print(f"Skipping {symbol} — no data or too little data.")
        conn.close()
        return None

    # Save data to DB
    # After downloading from yfinance
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)  # keep only first level like 'Close', 'Open', etc.

    print(data.columns)
    
    data.reset_index(inplace=True)  # Make sure "Date" is a column, not an index
    data.to_sql(symbol, conn, if_exists="replace", index=False)
    conn.close()

    data.set_index("Date", inplace=True)
    return generate_chart_and_signal(symbol, data)
    

"""def precompute_all():
    for symbol in popular_symbols:
        try:
            print(f"Precomputing {symbol}...")
            analyze_stock(symbol)
        except Exception as e:
            print(f"Failed on {symbol}: {e}")"""


def get_recommended_stocks() -> list:
    recommended = []

    for symbol in popular_symbols:
        signal = analyze_stock(symbol)
        if signal == "BULLISH - BUY":
            recommended.append(symbol)

    return recommended

def generate_chart_and_signal(symbol, data):
    data["MA5"] = data["Close"].rolling(window=5).mean()
    data["MA20"] = data["Close"].rolling(window=20).mean()
    data["Signal"] = 0
    data.loc[data["MA5"] > data["MA20"], "Signal"] = 1
    data.loc[data["MA5"] < data["MA20"], "Signal"] = -1

    latest_signal = data["Signal"].iloc[-1]

    # Save chart
    data[["Close", "MA5", "MA20"]].plot(figsize=(10, 5), title=f"{symbol} Price & MAs")
    plt.grid()
    plt.text(
        data.index[-1],
        data["Close"].iloc[-1] * 1.01,
        "BULLISH - BUY" if latest_signal == 1 else "SELL" if latest_signal == -1 else "HOLD",
        color="green" if latest_signal == 1 else "red" if latest_signal == -1 else "gray",
        fontsize=12,
        ha="right"
    )
    plt.savefig("static/output.png")
    plt.close()

    signal_label = "BULLISH - BUY" if latest_signal == 1 else "SELL" if latest_signal == -1 else "HOLD"
    return signal_label


import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sqlite3
import requests


popular_symbols = ["AAPL","MSFT","NVDA","GOOGL","AMZN","TSLA","META","BRK.B","JPM","V"]

def is_valid_stock(symbol):
    stock = yf.Ticker(symbol)
    try:
        info = stock.info
        return "longName" in info and info['regularMarketPrice'] is not None
    except Exception:
        return False

def check_stock(symbol):
    conn = sqlite3.connect("data/stock_data.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (symbol,)
    )
    
    if cursor.fetchone():
        cursor.execute(
            f"select MAX(Date) FROM '{symbol}'"
        )
        latest_date = cursor.fetchone()[0]
        if latest_date:
            latest_date = pd.to_datetime(latest_date)
            today = pd.Timestamp.today().normalize()

            if latest_date >= today - pd.Timedelta(days=1):
                data = pd.read_sql(f"SELECT * FROM '{symbol}'", conn, parse_dates=["Date"])
                
                generate_chart(symbol, data)
                conn.close()
                return generate_stock_signal(symbol, data)
    data = yf.download(symbol, period="6mo", interval="1d")
    if data.empty or len(data) < 20:
        return None
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data.reset_index(inplace=True)  # Make sure "Date" is a column, not an index
    data.to_sql(symbol, conn, if_exists="replace", index=False)
    conn.close()

    generate_chart(symbol, data)
    return generate_stock_signal(symbol, data)


#def analyze_stock(symbol):
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

def generate_chart(symbol, data):
    data["MA5"] = data["Close"].rolling(window=5).mean()
    data["MA20"] = data["Close"].rolling(window=20).mean()
    data["Signal"] = 0

    data.loc[data["MA5"] > data["MA20"], "Signal"] = 2
    data.loc[data["MA5"] < data["MA20"], "Signal"] = -2

    # Save chart
    data[["Close", "MA5", "MA20"]].plot(figsize=(10, 5), title=f"{symbol} Price & MAs")
    plt.grid()
    plt.savefig("static/output.png")
    plt.close()

def generate_stock_signal(symbol, data):
    if "Signal" not in data.columns or data.empty:
        return None
    signal = 0
    signal += avg_crossover(data)
    fair_value = generate_fair_value(symbol)
    if fair_value[0] < fair_value[1]:
        signal -= 1
    else:
        signal += 1
    vol = volatility(data)
    if vol < 0.01:
        signal += 1
    elif 0.01 <= vol <= 0.2:
        signal += 0
    else:
        signal -= 1
    if signal == 1:
        return "BULLISH- BUY"
    elif signal == 0:
        return "HOLD"
    else:
        return "SELL"
    

def avg_crossover(data):
    signal = data["Signal"].iloc[-1]
    return signal


def generate_fair_value(symbol):
    stock = yf.Ticker(symbol)
    try:
        eps = stock.info['trailingEps']
        sector = stock.info.get('sector')
        sector_pe = {
            "Technology": 30,
            "Financial Services": 15,
            "Healthcare": 20,
            "Energy": 12,
            "Industrials": 16,
        }
        if eps and eps > 0:
            industry_pe = sector_pe[sector]
            fair_value = round(eps * industry_pe, 2)

            conn = sqlite3.connect("data/stock_data.db")
            cursor = conn.cursor()
            cursor.execute(f'SELECT Close FROM "{symbol}" ORDER BY Date DESC LIMIT 1')
            row = cursor.fetchone()
            conn.close()

            if not row:
                print(f'no price data found for {symbol}')
                return None
            latest_price = row[0]
            return [fair_value, latest_price]
        else:
            return None
    except Exception as e:
        print(f"Error calculating fair value for {symbol}: {e}")
        return None
    
def volatility(data):
    data["Return"] = data["Close"].pct_change()
    volatility = data["Return"].std()
    return volatility


def get_recommended_stocks() -> list:
    recommended = []

    for symbol in popular_symbols:
        signal = check_stock(symbol)
        if signal > 0:
            recommended.append(symbol)

    return recommended


from datetime import datetime, timedelta

FINNHUB_API_KEY = "d1q3ptpr01qrh89nvv9gd1q3ptpr01qrh89nvva0"
def get_stock_news(symbol, limit=5):
    today = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')  # Last 7 days

    url = (
        f"https://finnhub.io/api/v1/company-news"
        f"?symbol={symbol}&from={from_date}&to={today}&token={FINNHUB_API_KEY}"
    )

    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = response.json()
            return news[:limit]
        else:
            print(f"Error fetching news: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception during news fetch: {e}")
        return []

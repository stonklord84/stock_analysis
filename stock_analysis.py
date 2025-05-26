import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3

def analyze_stock(symbol):
    data = yf.download(symbol, period="6mo", interval="1d")
    data["MA5"] = data["Close"].rolling(window=5).mean()
    data["MA20"] = data["Close"].rolling(window=20).mean()
    data["Signal"] = 0
    data.loc[data["MA5"] > data["MA20"], "Signal"] = 1
    data.loc[data["MA5"] < data["MA20"], "Signal"] = -1

    latest_signal = data["Signal"].iloc[-1]

    # Save to SQLite
    conn = sqlite3.connect("data/stock_data.db")
    data.to_sql(symbol, conn, if_exists="replace", index=True)
    conn.close()

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


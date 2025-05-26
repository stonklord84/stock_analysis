from flask import Flask, render_template, request
from stock_analysis import analyze_stock

#work is work
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    print("🔍 Route was reached")
    signal = None
    symbol = "NVDA"
    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        print(f"Analyzing: {symbol}")  # ADD THIS
        signal = analyze_stock(symbol)
    return render_template("index.html", signal=signal, symbol=symbol)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

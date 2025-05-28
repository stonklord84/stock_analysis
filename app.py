from flask import Flask, render_template, request
from stock_analysis import analyze_stock, get_recommended_stocks
import os

#work is work
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    signal = None
    symbol = ""
    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        print(f"Analyzing: {symbol}")  # ADD THIS
        signal = analyze_stock(symbol)

    return render_template("index.html", signal=signal, symbol=symbol)

@app.route("/recommend")
def recommended():
    recommended = get_recommended_stocks()
    return render_template("recommended.html", recommended=recommended)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

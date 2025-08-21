from flask import Flask, render_template, request, redirect, url_for, session
from stock_analysis import is_valid_stock, check_stock, generate_fair_value, volatility, get_recommended_stocks, get_stock_news
from flask_bcrypt import Bcrypt
import sqlite3
import os
import pandas as pd
from flask import flash

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "your_secret_key_here"  # Change this to something secure!

DB_PATH = "data/stock_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Login required decorator
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("homepage"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists. Try another one."
        conn.close()
        return redirect(url_for("homepage"))

    return render_template("register.html")

@app.route("/homepage", methods=["GET", "POST"])
def homepage():
    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "login":
            username = request.form["username"]
            password = request.form["password"]

            conn = get_db_connection()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()

            if user and bcrypt.check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("index"))
            else:
                return "Invalid credentials"
            
        elif form_type == "register":
            username = request.form["reg_username"]
            password = request.form["reg_password"]

            hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return "Username already exists. Try another one."
            conn.close()
            return redirect(url_for("homepage"))
        
    return render_template("login.html")
    

@app.route("/logout", methods=["POST"])
def logout():
    print('logout')
    if request.method == "POST":
        session.clear()
        return redirect(url_for("homepage"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    signal = None
    symbol = ""
    news = []

    user_id = session["user_id"]
    print(user_id, 'hi, user_id')

    conn = get_db_connection()
    watchlist_data = conn.execute("SELECT symbol FROM watchlist WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    symbols = [row["symbol"] for row in watchlist_data]

    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        if is_valid_stock(symbol):
            signal = check_stock(symbol)
            print(signal, 'this is the fucking signal')
        #signal = analyze_stock(symbol)
    else:
        if symbols:
            symbol = symbols[0]
            if is_valid_stock(symbol):
                signal = check_stock(symbol)
            #signal = analyze_stock(symbol)
            news = get_stock_news(symbol)

    return render_template("index.html", signal=signal, symbol=symbol, news=news)

@app.route("/statsForNerds", methods=["GET", "POST"])
@login_required
def statsForNerds():
    symbol = request.args.get("symbol", "").upper()
    fair_value = generate_fair_value(symbol)[0]
    latest_price = generate_fair_value(symbol)[1]
    signal = ''
    if latest_price >= fair_value:
        signal = 'Current price is overvalued'
    else:
        signal = 'Current price is undervalued'
    data = pd.read_sql(f"SELECT * FROM '{symbol}'", sqlite3.connect("data/stock_data.db"))
    vol = volatility(data)
    vol_str = ''
    if vol < 0.01:
        vol_str = 'low'
    if 0.01 <= vol <= 0.02:
        vol_str = 'medium'
    else:
        vol_str = 'high'

    # NEW: import and compute P/E
    from stock_analysis import pe_ratio
    pe_data = pe_ratio(symbol)  # dict: {pe, price, eps, eps_type, reason}

    return render_template(
        "statsForNerds.html",
        symbol=symbol,
        fair_value=fair_value,
        latest_price=latest_price,
        vol_str=vol_str,
        signal=signal,
        pe_data=pe_data  # 👈 pass to template
    )


@app.route("/recommend")
@login_required
def recommended():
    recommended = get_recommended_stocks()
    return render_template("recommended.html", recommended=recommended)


@app.route("/watchlist", methods=["GET", "POST"])
@login_required
def watchlist():
    user_id = session["user_id"]
    conn = get_db_connection()

    # Handle adding new symbols
    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        try:
            conn.execute("INSERT INTO watchlist (user_id, symbol) VALUES (?, ?)", (user_id, symbol))
            conn.commit()
            flash(f"Added {symbol} to your watchlist.")
        except sqlite3.IntegrityError:
            flash(f"{symbol} is already in your watchlist.")

    # Fetch all symbols in watchlist
    watchlist_data = conn.execute("SELECT symbol FROM watchlist WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    symbols = [row["symbol"] for row in watchlist_data]

    # Analyze each stock and get the signal
    signals = []
    for sym in symbols:
        try:
            if is_valid_stock(sym):
                signal = check_stock(sym)
        except Exception as e:
            signal = f"Error: {e}"
        signals.append({"symbol": sym, "signal": signal})

    return render_template("watchlist.html", signals=signals)


@app.route("/watchlist/remove/<symbol>", methods=["POST"])
@login_required
def remove_from_watchlist(symbol):
    user_id = session["user_id"]
    conn = get_db_connection()
    conn.execute("DELETE FROM watchlist WHERE user_id = ? AND symbol = ?", (user_id, symbol.upper()))
    conn.commit()
    conn.close()
    flash(f"Removed {symbol.upper()} from your watchlist.")
    return redirect(url_for("watchlist"))


from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return "Unknown"
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

from flask import Flask, render_template, request, redirect, url_for, session
from stock_analysis import analyze_stock, get_recommended_stocks
from flask_bcrypt import Bcrypt
import sqlite3
import os
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
            return redirect(url_for("login"))
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
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
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

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    signal = None
    symbol = ""
    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        signal = analyze_stock(symbol)

    return render_template("index.html", signal=signal, symbol=symbol)

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
            signal = analyze_stock(sym)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

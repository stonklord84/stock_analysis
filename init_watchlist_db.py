import sqlite3

conn = sqlite3.connect("data/stock_data.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    UNIQUE(user_id, symbol),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

conn.commit()
conn.close()

print("Watchlist table initialized.")

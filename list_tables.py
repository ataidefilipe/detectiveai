import sqlite3

conn = sqlite3.connect("game.db")

cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

tables = cursor.fetchall()

print([table[0] for table in tables])

conn.close()

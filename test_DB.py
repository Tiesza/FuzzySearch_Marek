import sqlite3

conn = sqlite3.connect("produkty.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM produkty")
pocet = cursor.fetchone()[0]
print(f"Počet záznamů v databázi: {pocet}")

cursor.execute("SELECT * FROM produkty LIMIT 5")
for row in cursor.fetchall():
    print(row)

conn.close()

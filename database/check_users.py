import sqlite3

conn = sqlite3.connect("database/login_auth.db")

cursor = conn.cursor()

cursor.execute("SELECT * FROM users")

users = cursor.fetchall()

for user in users:
    print(user)

conn.close()
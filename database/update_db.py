import sqlite3

conn = sqlite3.connect(
    r"c:\abhyas\LoginAuthSystem\database\login_auth.db"
)

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE users
ADD COLUMN last_login TIMESTAMP
""")

conn.commit()
conn.close()

print("last_login column added successfully!")
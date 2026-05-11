import bcrypt
from db import get_connection

conn = get_connection()
cur = conn.cursor()

password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

cur.execute("""
INSERT INTO users (username, password, role)
VALUES (?, ?, ?)
""", ("admin", password, "admin"))

conn.commit()
conn.close()
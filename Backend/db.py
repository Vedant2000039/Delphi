# # import mysql.connector
# from mysql.connector import pooling
# from dotenv import load_dotenv
# import os
# load_dotenv()

# DB_HOST = os.getenv("DB_HOST")
# DB_USER = os.getenv("DB_USER")
# DB_PASSWORD = os.getenv("DB_PASSWORD")
# DB_NAME = os.getenv("DB_NAME")

# dbconfig = {
#     "user": DB_USER,
#     "password": DB_PASSWORD,
#     "host": DB_HOST,
#     "database": DB_NAME,
# }
# connection_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)

# def get_conn():
#     return connection_pool.get_connection()

# print("db.py loaded ✅")



# db.py
from mysql.connector import pooling, Error
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if not (DB_HOST and DB_USER and DB_PASSWORD and DB_NAME):
    raise RuntimeError("DB config missing in environment (.env)")

dbconfig = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "database": DB_NAME,
    "raise_on_warnings": True,
    "autocommit": True,
    "ssl_disabled": True,
}

# a small connection pool
connection_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=20, **dbconfig)

def get_conn():
    try:
        return connection_pool.get_connection()
    except Error as e:
        raise

if __name__ == "__main__":
    # quick test (do NOT run on production via UI)
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("DB connection OK")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

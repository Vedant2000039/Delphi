import os
import mysql.connector
from dotenv import load_dotenv

# Load .env
load_dotenv()

# ============================================================
# MySQL Configuration
# ============================================================

MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "autocommit": True
}
# ============================================================
# OpenAI Configuration (Future)
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================================
# Explorium Configuration (Future)
# ============================================================

EXPLORIUM_API_KEY = os.getenv("EXPLORIUM_API_KEY")

# ============================================================
# Helper Function
# ============================================================

def get_db_connection():
    """
    Returns a new MySQL connection.
    """

    return mysql.connector.connect(**MYSQL_CONFIG)
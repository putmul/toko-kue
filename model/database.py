import mysql.connector


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
}


def get_connection():
    return mysql.connector.connect(database="sistem_transaksi", **DB_CONFIG)


def get_knowledge_connection():
    """Open a connection to the separate knowledge-management database."""
    return mysql.connector.connect(
        database="knowledge_management",
        **DB_CONFIG
    )

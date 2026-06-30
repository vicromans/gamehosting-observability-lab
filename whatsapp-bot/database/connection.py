import pymysql


DB_CONFIG = {
    "host": "mariadb",
    "user": "gameuser",
    "password": "gamepass123",
    "database": "gamehosting",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

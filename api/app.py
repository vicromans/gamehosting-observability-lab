from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics
import mysql.connector
import os
import requests

app = Flask(__name__)

metrics = PrometheusMetrics(app)

def get_db_connection():
    return mysql.connector.connect(
        host="mariadb",
        user="gameuser",
        password="gamepass123",
        database="gamehosting"
    )

@app.route("/")
def home():
    return {"message": "Game Hosting API funcionando"}

@app.route("/health")
def health():
    try:
        conn = mysql.connector.connect(
            host="mariadb",
            user="gameuser",
            password="gamepass123",
            database="gamehosting"
        )
        conn.close()
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}, 500

@app.route("/servers")
def servers():
    conn = mysql.connector.connect(
        host="mariadb",
        user="gameuser",
        password="gamepass123",
        database="gamehosting"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM servers")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

@app.route("/bitcoin")
def bitcoin():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin",
            "vs_currencies": "usd"
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()
        price = data["bitcoin"]["usd"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bitcoin_prices (price_usd, source) VALUES (%s, %s)",
            (price, "coingecko")
        )
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "asset": "bitcoin",
            "currency": "usd",
            "price": price,
            "source": "coingecko",
            "saved": True
        }, 200

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

@app.route("/bitcoin/history")
def bitcoin_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, price_usd, source, created_at
            FROM bitcoin_prices
            ORDER BY created_at DESC
            LIMIT 20
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(rows), 200

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

@app.route("/bitcoin/stats")
def bitcoin_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                COUNT(*) AS records,
                MIN(price_usd) AS min_price,
                MAX(price_usd) AS max_price,
                AVG(price_usd) AS avg_price,
                (SELECT price_usd FROM bitcoin_prices ORDER BY created_at DESC LIMIT 1) AS latest_price,
                (SELECT created_at FROM bitcoin_prices ORDER BY created_at DESC LIMIT 1) AS latest_time
            FROM bitcoin_prices
        """)

        row = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify(row), 200

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

@app.route("/bitcoin/check/<threshold>")
def bitcoin_check(threshold):
    threshold = float(threshold)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT price_usd, created_at
            FROM bitcoin_prices
            ORDER BY created_at DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if not row:
            return {"status": "no_data"}, 404

        price = float(row["price_usd"])

        return {
            "asset": "bitcoin",
            "latest_price": price,
            "threshold": threshold,
            "alert": price < threshold,
            "message": "Bitcoin below threshold" if price < threshold else "Bitcoin above threshold",
            "created_at": str(row["created_at"])
        }, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

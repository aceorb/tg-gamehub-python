import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, sslmode='require')
    return conn


def insert_user(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (telegram_id, daily_predictions, last_prediction_date) 
        VALUES (%s, 0, CURRENT_DATE) 
        ON CONFLICT (telegram_id) 
        DO NOTHING;
    """, (telegram_id,))
    conn.commit()
    cur.close()
    conn.close()


def update_checkin_date(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET checkin_date = CURRENT_DATE, daily_predictions = daily_predictions + 1 
        WHERE telegram_id = %s;
    """, (telegram_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_user_checkin_date(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT checkin_date FROM users WHERE telegram_id = %s;", (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result


def insert_price_alert(telegram_id, contract_address, alert_price):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO price_alerts (telegram_id, contract_address, alert_price) 
        VALUES (%s, %s, %s);
    """, (telegram_id, contract_address, alert_price))
    conn.commit()
    cur.close()
    conn.close()


def get_price_alerts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM price_alerts WHERE alert_active = TRUE;")
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result


def deactivate_price_alert(alert_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE price_alerts SET alert_active = FALSE WHERE alert_id = %s;", (alert_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_user_predictions(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT daily_predictions, last_prediction_date 
        FROM users 
        WHERE telegram_id = %s;
    """, (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result


def update_user_predictions(telegram_id, predictions):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET daily_predictions = %s, last_prediction_date = CURRENT_DATE 
        WHERE telegram_id = %s;
    """, (predictions, telegram_id))
    conn.commit()
    cur.close()
    conn.close()


def add_to_portfolio(telegram_id, contract_address):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO portfolio (telegram_id, contract_address) 
        VALUES (%s, %s);
    """, (telegram_id, contract_address))
    conn.commit()
    cur.close()
    conn.close()


def remove_from_portfolio(telegram_id, contract_address):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM portfolio 
        WHERE telegram_id = %s AND contract_address = %s;
    """, (telegram_id, contract_address))
    conn.commit()
    cur.close()
    conn.close()


def get_user_portfolio(telegram_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT contract_address FROM portfolio WHERE telegram_id = %s;", (telegram_id,))
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result


def reset_user_predictions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET daily_predictions = 0;")
    conn.commit()
    cur.close()
    conn.close()


def set_user_predictions(telegram_id, predictions):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET daily_predictions = %s WHERE telegram_id = %s;", (predictions, telegram_id))
    conn.commit()
    cur.close()
    conn.close()


def set_user_suggestion(telegram_id, suggestion):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO suggestions (telegram_id, text, date)  VALUES (%s, %s, CURRENT_DATE);", (telegram_id, suggestion))
    conn.commit()
    cur.close()
    conn.close()

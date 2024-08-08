import os
import logging
import openai
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from telegram.error import NetworkError, RetryAfter, Conflict
from database import insert_user, update_checkin_date, insert_price_alert, get_price_alerts, deactivate_price_alert, get_user_predictions, update_user_predictions, reset_user_predictions, add_to_portfolio, remove_from_portfolio, get_user_portfolio, get_user_checkin_date, set_user_predictions
from pycoingecko import CoinGeckoAPI
import time
from datetime import datetime, timedelta
import threading

# Load secrets from Railway environment variables
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
ADMIN_USER_ID = 751510914

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize CoinGeckoAPI
cg = CoinGeckoAPI()

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Rate limiting dictionary
user_request_times = {}

def rate_limited(user_id):
    now = time.time()
    if user_id in user_request_times:
        last_request_time = user_request_times[user_id]
        if now - last_request_time < 10:  # 10 seconds between requests
            return True
    user_request_times[user_id] = now
    return False

# Main menu
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton("✨ Daily Check-in ✨", callback_data='daily_checkin')],
        [InlineKeyboardButton("📰 Daily Crypto News 📰", callback_data='daily_crypto_news')],
        [InlineKeyboardButton("📈 Price Alert 📉", callback_data='price_alert')],
        [InlineKeyboardButton("💡 Crypto Tips 💡", callback_data='crypto_tips')],
        [InlineKeyboardButton("🔮 AI Prediction 🔮", callback_data='ai_prediction')],
        [InlineKeyboardButton("💼 My Portfolio 💼", callback_data='my_portfolio')]
    ]
    
    if user_id == ADMIN_USER_ID:
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel 🔧", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        '🎉 Welcome to the Crypto Prediction Bot! 🎉\nStay updated with daily crypto news, set price alerts, and get AI predictions. Choose an option below:',
        reply_markup=reply_markup
    )

# Handlers for buttons
def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'daily_checkin':
        handle_daily_checkin(query, context)
    elif query.data == 'daily_crypto_news':
        handle_daily_crypto_news(query, context)
    elif query.data == 'price_alert':
        handle_price_alert(query, context)
    elif query.data == 'crypto_tips':
        handle_crypto_tips(query, context)
    elif query.data == 'ai_prediction':
        handle_ai_prediction(query, context)
    elif query.data == 'my_portfolio':
        handle_my_portfolio(query, context)
    elif query.data == 'admin_panel':
        handle_admin_panel(query, context)
    elif query.data == 'home':
        show_main_menu(query, context)
    elif query.data == 'add_price_alert':
        query.edit_message_text(text="Enter the contract address and the price you want to set an alert for, separated by a space (e.g., '0x514910771af9ca656af840dff83e8264ecf986ca 500'):")
        context.user_data['awaiting_price_alert'] = True
    elif query.data == 'remove_price_alert':
        query.edit_message_text(text="Enter the alert ID you want to remove:")
        context.user_data['awaiting_remove_alert'] = True
    elif query.data == 'add_to_portfolio':
        query.edit_message_text(text="Enter the contract address to add to your portfolio:")
        context.user_data['awaiting_portfolio_add'] = True
    elif query.data == 'remove_from_portfolio':
        query.edit_message_text(text="Enter the contract address to remove from your portfolio:")
        context.user_data['awaiting_portfolio_remove'] = True
    elif query.data == 'reset_daily_predictions':
        reset_user_predictions()
        query.edit_message_text(text="Daily predictions have been reset.")
    elif query.data == 'set_admin_predictions':
        set_user_predictions(ADMIN_USER_ID, 40)
        query.edit_message_text(text="Admin daily predictions limit has been set to 40.")

def show_main_menu(query, context):
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton("✨ Daily Check-in ✨", callback_data='daily_checkin')],
        [InlineKeyboardButton("📰 Daily Crypto News 📰", callback_data='daily_crypto_news')],
        [InlineKeyboardButton("📈 Price Alert 📉", callback_data='price_alert')],
        [InlineKeyboardButton("💡 Crypto Tips 💡", callback_data='crypto_tips')],
        [InlineKeyboardButton("🔮 AI Prediction 🔮", callback_data='ai_prediction')],
        [InlineKeyboardButton("💼 My Portfolio 💼", callback_data='my_portfolio')]
    ]
    
    if user_id == ADMIN_USER_ID:
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel 🔧", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        '🎉 Welcome to the Crypto Prediction Bot! 🎉\nStay updated with daily crypto news, set price alerts, and get AI predictions. Choose an option below:',
        reply_markup=reply_markup
    )

def handle_daily_checkin(query, context):
    user_id = query.from_user.id
    insert_user(user_id)
    user_checkin_date = get_user_checkin_date(user_id)
    if user_checkin_date and user_checkin_date['checkin_date'] == datetime.now().strftime('%Y-%m-%d'):
        query.edit_message_text(text="Sorry, you have already checked in today. Please come back tomorrow.")
    else:
        update_checkin_date(user_id)
        keyboard = [[InlineKeyboardButton("🏠 Return to Home", callback_data='home')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="✅ You've checked in today! You earned 1 extra daily prediction.", reply_markup=reply_markup)

def handle_daily_crypto_news(query, context):
    news = fetch_crypto_news()
    summary = summarize_news(news)
    keyboard = [[InlineKeyboardButton("🏠 Return to Home", callback_data='home')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=summary, reply_markup=reply_markup)

def fetch_crypto_news():
    url = f'https://newsapi.org/v2/everything?q=cryptocurrency&apiKey={NEWSAPI_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {"status": "error"}

def summarize_news(news):
    if "status" in news and news["status"] == "error":
        return "Error fetching news."

    articles = [article['title'] + " " + article['description'] for article in news['articles'][:5]]
    news_summary = " ".join(articles)
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Summarize this news: {news_summary}"}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

def handle_price_alert(query, context):
    keyboard = [
        [InlineKeyboardButton("Add Price Alert", callback_data='add_price_alert')],
        [InlineKeyboardButton("Remove Price Alert", callback_data='remove_price_alert')],
        [InlineKeyboardButton("🏠 Return to Home", callback_data='home')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Manage your price alerts:", reply_markup=reply_markup)

def handle_crypto_tips(query, context):
    tips = get_crypto_tips()
    keyboard = [[InlineKeyboardButton("🏠 Return to Home", callback_data='home')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=tips, reply_markup=reply_markup)

def get_crypto_tips():
    return "Here are some crypto tips: ...\n1. Do your research.\n2. Diversify your portfolio.\n3. Use a secure wallet.\n4. Stay updated with news."

def handle_ai_prediction(query, context):
    user_id = query.from_user.id
    user_predictions = get_user_predictions(user_id)
    if user_predictions is not None:
        max_predictions = 40 if user_id == ADMIN_USER_ID else 10
        remaining_predictions = max_predictions - user_predictions['daily_predictions']
        if user_predictions['daily_predictions'] >= max_predictions:
            keyboard = [[InlineKeyboardButton("🏠 Return to Home", callback_data='home')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text=f"You've reached your daily limit of {max_predictions} AI predictions. Please check in tomorrow for more predictions.", reply_markup=reply_markup)
            return

        keyboard = [[InlineKeyboardButton("🏠 Return to Home", callback_data='home')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=(
                "🔮 AI Prediction\n\n"
                "Provide a contract address of a cryptocurrency to get an AI-based prediction of its future performance.\n"
                "Example: `0x514910771af9ca656af840dff83e8264ecf986ca`\n"
                "Note: This prediction is not financial advice. Please do your own research before making any investment decisions.\n\n"
                f"Remaining predictions for today: {remaining_predictions}"
            ),
            reply_markup=reply_markup
        )
    context.user_data['awaiting_contract_address'] = True

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if rate_limited(user_id):
        update.message.reply_text("Please wait a moment before making another request.")
        return

    if context.user_data.get('awaiting_contract_address'):
        contract_address = update.message.text
        prediction = get_ai_prediction(contract_address)
        context.user_data['awaiting_contract_address'] = False

        user_predictions = get_user_predictions(user_id)
        max_predictions = 40 if user_id == ADMIN_USER_ID else 10
        update_user_predictions(user_id, user_predictions['daily_predictions'] + 1)
        remaining_predictions = max_predictions - (user_predictions['daily_predictions'] + 1)

        keyboard = [[InlineKeyboardButton("🏠 Return to Home", callback_data='home')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            text=(
                f"🔮 AI Prediction:\n{prediction}\n\n"
                "This prediction is generated by AI and is not financial advice. "
                "Please do your own research before making any investment decisions.\n\n"
                f"Remaining predictions for today: {remaining_predictions}"
            ),
            reply_markup=reply_markup
        )
    elif context.user_data.get('awaiting_portfolio_add'):
        contract_address = update.message.text
        if len(contract_address) <= 42:
            add_to_portfolio(user_id, contract_address)
            context.user_data['awaiting_portfolio_add'] = False
            update.message.reply_text(f"Added {contract_address} to your portfolio.")
        else:
            update.message.reply_text(f"Contract address '{contract_address}' is too long. Must be at most 42 characters.")

    elif context.user_data.get('awaiting_portfolio_remove'):
        contract_address = update.message.text
        remove_from_portfolio(user_id, contract_address)
        context.user_data['awaiting_portfolio_remove'] = False
        update.message.reply_text(f"Removed {contract_address} from your portfolio.")

    elif context.user_data.get('awaiting_price_alert'):
        try:
            contract_address, alert_price = update.message.text.split()
            alert_price = float(alert_price)
            insert_price_alert(user_id, contract_address, alert_price)
            update.message.reply_text(f"Price alert set for {contract_address} at ${alert_price}.")
        except ValueError:
            update.message.reply_text("Invalid input. Please enter the contract address and the price separated by a space (e.g., '0x514910771af9ca656af840dff83e8264ecf986ca 500').")
        context.user_data['awaiting_price_alert'] = False

    elif context.user_data.get('awaiting_remove_alert'):
        try:
            alert_id = int(update.message.text)
            deactivate_price_alert(alert_id)
            update.message.reply_text(f"Price alert with ID {alert_id} removed.")
        except ValueError:
            update.message.reply_text("Invalid input. Please enter a valid alert ID.")
        context.user_data['awaiting_remove_alert'] = False

def get_ai_prediction(contract_address):
    try:
        coin_data = cg.get_coin_info_from_contract_address_by_id(id='ethereum', contract_address=contract_address)
        if 'error' in coin_data:
            return "Coin not found. Please check the contract address and try again."
        
        market_data = coin_data.get('market_data', {})
        current_price = market_data.get('current_price', {}).get('usd', 'N/A')
        market_cap = market_data.get('market_cap', {}).get('usd', 'N/A')
        total_volume = market_data.get('total_volume', {}).get('usd', 'N/A')

        price_change_percentage_24h = market_data.get('price_change_percentage_24h', 'N/A')
        market_cap_change_percentage_24h = market_data.get('market_cap_change_percentage_24h', 'N/A')

        coin_info = f"Current Price: ${current_price}\nMarket Cap: ${market_cap}\nTotal Volume: ${total_volume}\nPrice Change Percentage 24H: {price_change_percentage_24h}\nMarket Cap Change Percentage 24H: {market_cap_change_percentage_24h}\n"
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Based on the following data, predict the future performance of the cryptocurrency:\n{coin_info}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        return f"Error fetching data: {str(e)}"

def handle_my_portfolio(query, context):
    user_id = query.from_user.id
    portfolio = get_user_portfolio(user_id)
    if not portfolio:
        portfolio_text = "Your portfolio is empty. Add some tokens to track."
    else:
        portfolio_text = "Your Portfolio:\n"
        total_value = 0
        for coin in portfolio:
            try:
                coin_data = cg.get_coin_info_from_contract_address_by_id(id='ethereum', contract_address=coin['contract_address'])
                if 'error' in coin_data:
                    portfolio_text += f"- {coin['contract_address']}: Coin not found\n"
                    continue

                current_price = coin_data['market_data']['current_price']['usd']
                portfolio_text += f"- {coin['contract_address']}: ${current_price}\n"
                total_value += current_price
            except Exception as e:
                logging.error(f"Error fetching data for {coin['contract_address']}: {str(e)}")
                portfolio_text += f"- {coin['contract_address']}: Error fetching data\n"

        portfolio_text += f"\nTotal Portfolio Value: ${total_value}\n\n"
        portfolio_text += "History of coins in the last 24 hours:\n"
        for coin in portfolio:
            try:
                history = cg.get_coin_market_chart_range_by_id(
                    id=coin['contract_address'],
                    vs_currency='usd',
                    from_timestamp=int(time.time()) - 24 * 60 * 60,
                    to_timestamp=int(time.time())
                )
                prices = history['prices']
                portfolio_text += f"- {coin['contract_address']}:\n"
                for timestamp, price in prices:
                    portfolio_text += f"  {datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')}: ${price}\n"
            except Exception as e:
                logging.error(f"Error fetching historical data for {coin['contract_address']}: {str(e)}")
                portfolio_text += f"- {coin['contract_address']}: Error fetching historical data\n"

    keyboard = [
        [InlineKeyboardButton("Add to Portfolio", callback_data='add_to_portfolio')],
        [InlineKeyboardButton("Remove from Portfolio", callback_data='remove_from_portfolio')],
        [InlineKeyboardButton("🏠 Return to Home", callback_data='home')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=portfolio_text, reply_markup=reply_markup)

def handle_admin_panel(query, context):
    keyboard = [
        [InlineKeyboardButton("Reset Daily Predictions", callback_data='reset_daily_predictions')],
        [InlineKeyboardButton("Set Admin Predictions to 40", callback_data='set_admin_predictions')],
        [InlineKeyboardButton("🏠 Return to Home", callback_data='home')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="🔧 Admin Panel 🔧", reply_markup=reply_markup)

def reset_predictions_daily():
    while True:
        now = datetime.now()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_until_reset = (next_reset - now).total_seconds()
        time.sleep(time_until_reset)
        reset_user_predictions()

import threading
threading.Thread(target=reset_predictions_daily, daemon=True).start()

def main() -> None:
    updater = Updater(TELEGRAM_API_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    def run():
        while True:
            try:
                updater.start_polling()
                updater.idle()
            except Conflict:
                logging.error("Conflict: Another bot instance is already running.")
                break
            except NetworkError:
                logging.error("Network error occurred. Retrying in 5 seconds...")
                time.sleep(5)
            except RetryAfter as e:
                logging.error(f"Rate limited by Telegram. Retrying in {e.retry_after} seconds...")
                time.sleep(e.retry_after)
            except Exception as e:
                logging.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    run()

if __name__ == '__main__':
    main()

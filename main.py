import os, json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CallbackContext

from telegram import  Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import time
from dotenv import load_dotenv

# Load secrets from Railway environment variables
load_dotenv()
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Rate limiting dictionary
user_request_times = {}

# Keyboard Button Dict with Callback
keyboard_dict = {
    'home': [InlineKeyboardButton("🏠 Sports 🏠", web_app=WebAppInfo("https://sports-betting-dusky.vercel.app/"))],
    'favourites': [InlineKeyboardButton("📰 Favourites 📰", web_app=WebAppInfo("https://sports-betting-dusky.vercel.app/"))],
    'ai': [InlineKeyboardButton("📈 AI 📉", web_app=WebAppInfo("https://sports-betting-dusky.vercel.app/"))],
    'betslip': [InlineKeyboardButton("💡 Betslip 💡", web_app=WebAppInfo("https://sports-betting-dusky.vercel.app/"))],
    'my_bets': [InlineKeyboardButton("💼 My Bets 💼", web_app=WebAppInfo("https://sports-betting-dusky.vercel.app/"))],
}


def generate_main_menu(user_id):
    keyboard = [
        generate_keyboard_button('home'),
        generate_keyboard_button('favourites'),
        generate_keyboard_button('ai'),
        generate_keyboard_button('betslip'),
        generate_keyboard_button('my_bets'),
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    return (
        '🎉 Welcome to the only one TG Gamehub Bot! 🎉\nStay updated with us. Choose an '
        'option below:',
        reply_markup
    )


def generate_return_home_reply_markup():
    keyboard = [generate_keyboard_button('home')]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def generate_keyboard_button(keyboard_type):
    return keyboard_dict.get(keyboard_type, None)


def generate_keyboard_button_for_portfolio_remove(contract):
    return [InlineKeyboardButton(contract, callback_data='remove_contract_'+contract)]


def rate_limited(user_id):
    now = time.time()
    if user_id in user_request_times:
        last_request_time = user_request_times[user_id]
        if now - last_request_time < 10:  # 10 seconds between requests
            return True
    user_request_times[user_id] = now
    return False


# Main menu
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    (message, reply_markup) = generate_main_menu(user_id)
    await update.message.reply_text(message, reply_markup=reply_markup)


# Handlers for buttons
def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'home':
        handle_home(query, context)
    elif query.data == 'favourites':
        handle_favourites(query, context)
    elif query.data == 'ai':
        handle_ai(query, context)
    elif query.data == 'betslip':
        handle_betslip(query, context)
    elif query.data == 'my_bets':
        handle_my_bets(query, context)

def handle_message(update: Update, context: CallbackContext) -> None:
    pass


def show_main_menu(query, context):
    user_id = query.from_user.id
    (message, reply_markup) = generate_main_menu(user_id)
    query.edit_message_text(message, reply_markup=reply_markup)


def handle_home(query, context):
    user_id = query.from_user.id
    query.edit_message_text(text="Home clicked")

def handle_favourites(query, context):
    user_id = query.from_user.id

def handle_ai(query, context):
    user_id = query.from_user.id

def handle_betslip(query, context):
    user_id = query.from_user.id

def handle_my_bets(query, context):
    user_id = query.from_user.id

# Handle incoming WebAppData
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Print the received data and remove the button."""
    # Here we use `json.loads`, since the WebApp sends the data JSON serialized string
    # (see webappbot.html)
    data = json.loads(update.effective_message.web_app_data.data)
    await update.message.reply_html(
        text=f"You selected the color with the HEX value <code>{data['hex']}</code>. The "
             f"corresponding RGB value is <code>{tuple(data['rgb'].values())}</code>."
    )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    print(f"TOKEN:{TELEGRAM_API_TOKEN}")
    application = Application.builder().token(TELEGRAM_API_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()



if __name__ == '__main__':
    main()
import os
import logging
import time
import smtplib
import sqlite3
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from dotenv import load_dotenv

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        #logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# Configuration
load_dotenv()  # Charge les variables d'environnement à partir du fichier .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID")
#NOTIFICATION_INTERVAL = 604800  # 7 jours en secondes
NOTIFICATION_INTERVAL = 30  

# Database setup (optional)
def setup_database():
    conn = sqlite3.connect('notifications.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY,
            responded INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Function to send Telegram message
def send_telegram_message(chat_id, message):
    logger.info(f"Sending message to {chat_id}: {message}")
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Message sent successfully to {chat_id}")
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")

# Function to send email
def send_email(recipient, subject, body):
    logger.info(f"Sending message to {chat_id}: {message}")
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipient, f"Subject: {subject}\n\n{body}")

# Command handler for Telegram to stop notification
def stop_notification(update, context):
    update.message.reply_text("Merci, vous avez confirmé que tout va bien.")
    # Update the database status here (e.g., set responded to 1)

# Main application loop
def main():
    logger.info("Starting the application...")
    setup_database()
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('stop', stop_notification))

    updater.start_polling()

    while True:
        # Logic to send notification and email
        time.sleep(NOTIFICATION_INTERVAL)
        send_telegram_message(YOUR_CHAT_ID, "Tout va bien? Répondez avec /stop pour arrêter.")
        # Wait for a response, check the database for responses

if __name__ == '__main__':
    main()
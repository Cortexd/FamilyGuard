import os
import logging
import time
import smtplib
import sqlite3
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configuration
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID")
NOTIFICATION_INTERVAL = 3600  # 1 heure en secondes

# États de la conversation
CHOOSING, TYPING_REPLY = range(2)

# Mode de fonctionnement par défaut
MODE = "arret"
DAYS_ACTIVE = 1  # Nombre de jours par défaut pour le mode "activé"

# Database setup
def setup_database():
    logger.info("Setup database")
    conn = sqlite3.connect('notifications.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY,
            responded INTEGER DEFAULT 0,
            last_notified DATETIME
        )
    ''')
    conn.commit()
    conn.close()

# Fonction pour envoyer un message Telegram
def send_telegram_message(chat_id, message):
    logger.info(f"Sending message to {chat_id}: {message}")
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Message sent successfully to {chat_id}")
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")

# Fonction pour envoyer un email
def send_email(recipient, subject, body):
    logger.info(f"Sending email to {recipient}: {subject}")
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipient, f"Subject: {subject}\n\n{body}")

# Commande pour commencer la conversation
def start(update, context):
    update.message.reply_text(
        "Bienvenue dans le système de notifications !\n"
        "Voici comment cela fonctionne :\n"
        "1. Activez les notifications en utilisant la commande /start.\n"
        "2. Spécifiez le nombre de jours pendant lesquels vous souhaitez recevoir des notifications (entre 1 et 4).\n"
        "3. Recevez des notifications régulières pour vérifier votre état.\n"
        "4. Utilisez /stop pour arrêter les notifications à tout moment.\n"
        "Veuillez maintenant spécifier le nombre de jours."
    )
    return CHOOSING

# Fonction pour gérer le nombre de jours choisi
def receive_days(update, context):
    global DAYS_ACTIVE, MODE
    if update.message.text.isdigit():
        DAYS_ACTIVE = int(update.message.text)
        if 1 <= DAYS_ACTIVE <= 4:
            MODE = "active"
            update.message.reply_text(f"Mode activé pour {DAYS_ACTIVE} jours.")
            welcome_message(update.message.chat_id)  # Message de bienvenue
            return ConversationHandler.END
        else:
            update.message.reply_text("Veuillez entrer un nombre de jours entre 1 et 4.")
    else:
        update.message.reply_text("Veuillez entrer un nombre valide (1-4).")
    return CHOOSING

# Commande pour stopper les notifications
def stop(update, context):
    global MODE
    MODE = "arret"
    update.message.reply_text("Mode arrêté. Vous ne recevrez plus de notifications.")
    welcome_message(update.message.chat_id)  # Envoyer le message d'accueil après arrêt
    return ConversationHandler.END

# Fonction pour envoyer le message d'accueil
def welcome_message(chat_id):
    message = (
        "Fonctionnement de l'application :\n"
        "1. Vous êtes maintenant en mode 'actif' et recevrez des mises à jour régulières.\n"
        "2. Le nombre de jours que vous avez spécifié est de {DAYS_ACTIVE}.\n"
        "3. Utilisez /stop pour arrêter les notifications."
    )
    send_telegram_message(chat_id, message)

# Logic to handle notifications based on the mode
def check_notifications():
    conn = sqlite3.connect('notifications.db')
    cursor = conn.cursor()
    
    if MODE == "arret":
        return

    last_notified_time = datetime.now() - timedelta(days=DAYS_ACTIVE)
    
    cursor.execute("SELECT responded FROM responses WHERE id = 1")  # Assume id = 1
    response_state = cursor.fetchone()
    
    if response_state and response_state[0] == 0:
        if last_notified_time > response_state:
            send_email(EMAIL_ADDRESS, "Pas de réponse reçue", "Aucune réponse n'a été reçue concernant votre état.")
    
    conn.commit()
    conn.close()

# Main application loop
def main():
    logger.info("Starting the application...")
    setup_database()
    
    # Envoyer une notification au démarrage
    welcome_message(YOUR_CHAT_ID)

    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [MessageHandler(Filters.text, receive_days)],
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()

    while True:
        if MODE == "active":
            send_telegram_message(YOUR_CHAT_ID, "Tout va bien? Répondez avec /stop pour arrêter.")
            check_notifications()
            
        time.sleep(NOTIFICATION_INTERVAL)

if __name__ == '__main__':
    main()
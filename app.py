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
RECEIVER_EMAIL_ADDRESS = os.getenv("RECEIVER_EMAIL_ADDRESS")
SENDER_EMAIL_ADDRESS = os.getenv("SENDER_EMAIL_ADDRESS")
SENDER_EMAIL_PASSWORD = os.getenv("SENDER_EMAIL_PASSWORD")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID")
NOTIFICATION_INTERVAL = 3600  # 1 heure entre les notifications

# États de la conversation
CHOOSING, TYPING_REPLY = range(2)

# Mode de fonctionnement
MODE = "arret"
DAYS_ACTIVE = 1  # Nombre de jours par défaut pour le mode "activé"
notification_times = ['09:00', '10:00', '12:00', '19:00', 
                      '19:01', '19:02', '19:03', '19:04', 
                      '19:05', '19:06']  # Heures de notification

# Setup de la base de données
def setup_database():
    logger.info("Setting up the database...")
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
    logger.info("Database setup completed.")

# Fonction pour envoyer un message Telegram
def send_telegram_message(chat_id, message):
    logger.info(f"Sending message to {chat_id}: {message}")
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=chat_id, text=message, parse_mode='markdown' )
        logger.info(f"Message sent successfully to {chat_id}")
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")

# Fonction pour envoyer un e-mail
def send_email(recipient, subject, body):
    logger.info(f"Sending email to {recipient}: {subject}")
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL_ADDRESS, SENDER_EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL_ADDRESS, recipient, f"Subject: {subject}\n\n{body}")
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Error sending email: {e}")

# Commande pour commencer la conversation
def start(update, context):
    logger.info("Starting conversation with user.")
    update.message.reply_text(
        "Spécifiez le nombre de jours entre 1 et 10.\n"
        "Passé ce delais, vous recevrez des notifications régulières à 9H, 10H, 12H, 19H et ainsi de suite.\n"
        "Si vous ne confirmez pas votre état, un e-mail sera envoyé à 20H.\n"
        "Raccourcis /start /stop /info."
    )
    return CHOOSING

# Fonction pour gérer le nombre de jours choisi
def receive_days(update, context):
    global DAYS_ACTIVE, MODE
    logger.info(f"User entered number of days: {update.message.text}")
    
    if update.message.text.isdigit():
        DAYS_ACTIVE = int(update.message.text)
        if 1 <= DAYS_ACTIVE <= 10:
            MODE = "active"
            update.message.reply_text(f"Mode activé pour {DAYS_ACTIVE} jours.")
            logger.info(f"Notifications activated for {DAYS_ACTIVE} days.")
            return ConversationHandler.END
        else:
            update.message.reply_text("Veuillez entrer un nombre de jours entre 1 et 10.")
    else:
        update.message.reply_text("Veuillez entrer un nombre valide (1-10).")
    return CHOOSING

# Commande pour stopper les notifications
def stop(update, context):
    global MODE
    MODE = "arret"
    logger.info("Stopping notifications.")
    update.message.reply_text("Mode arrêté. Vous ne recevrez plus de notifications.\n Raccourcis /start /stop /info.")
    return ConversationHandler.END


# Fonction pour envoyer un message d'info
# TODO : Ajouter en mode start les infos de délais : premiere alerte le ...
def info_message(update, context):
    message = (
        f"Fonctionnement de l'application :\n"
        f"Mode actuel *{MODE}* {'🛑' if MODE == 'arret' else '✅'}.\n"
        f"Nombre de jours spécifié : *{DAYS_ACTIVE}* jours.\n"
        f"Raccourcis /start /stop /info."
    )
    send_telegram_message(update.message.chat_id, message)

# Fonction pour envoyer un message de démarrage
def welcome_message(chat_id):
    message = (
        f"Fonctionnement de l'application :\n"
        f"Utilisez /start pour démarrer la surveillance.\n"
        f"Utilisez /stop pour arrêter les notifications.\n"
        f"Utilisez /info pour avoir le status actuel."
    )
    send_telegram_message(chat_id, message)

# Fonction pour vérifier les notifications
def check_notifications():
    conn = sqlite3.connect('notifications.db')
    cursor = conn.cursor()

    # Envoyer des messages si en mode "actif"
    if MODE == "active":
        current_time = datetime.now()
        notification_hour = current_time.strftime("%H:%M")
        logger.info(f"Checking notifications at {notification_hour}")

        # Vérifier si c'est l'heure d'envoyer un message
        if notification_hour in notification_times:
            send_telegram_message(YOUR_CHAT_ID, "Tout va bien? Répondez avec /stop si tout va bien.")

            # Si réponse non reçue, vérifier et envoyer l'email
            cursor.execute("SELECT responded FROM responses WHERE id = 1")  # Assume id = 1
            response_state = cursor.fetchone()

            if response_state and response_state[0] == 0:
                logger.info("No response received. Checking if email must be sent.")
                if current_time.hour == 20:
                    send_email(RECEIVER_EMAIL_ADDRESS, "Pas de réponse reçue", "Aucune réponse n'a été reçue concernant votre état.")

    conn.commit()
    conn.close()

# Boucle principale de l'application
def main():
    logger.info("Starting the application...")
    setup_database()
    
    # Gestion télégram
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [MessageHandler(Filters.text, receive_days)],
        },
        fallbacks=[CommandHandler('stop', stop)],
    )
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('info', info_message))  # Ajouter le handler pour /info
    updater.start_polling()
    

    welcome_message(YOUR_CHAT_ID)

    while True:
        check_notifications()
        time.sleep(NOTIFICATION_INTERVAL)

if __name__ == '__main__':
    main()
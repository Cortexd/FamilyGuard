import os
import logging
import time
import locale
import smtplib
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

# Configurer la locale
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')  # Pour Linux

# Configuration
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RECEIVER_EMAIL_ADDRESS = os.getenv("RECEIVER_EMAIL_ADDRESS")
SENDER_EMAIL_ADDRESS = os.getenv("SENDER_EMAIL_ADDRESS")
SENDER_EMAIL_PASSWORD = os.getenv("SENDER_EMAIL_PASSWORD")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID")
CHECK_NOTIFICATION_INTERVAL = 5  # en seconde

# États de la conversation
CHOOSING, TYPING_REPLY = range(2)

# Mode de fonctionnement
MODE = "arret"
DAYS_ACTIVE = 1  # Nombre de jours par défaut pour le mode "activé"
# notification_times = ['09:00', '10:00', '12:00', '19:00', 
#                       '19:01', '19:02', '19:03', '19:04', 
#                       '19:05', '19:06']  # Heures de notification
notification_times = ['12:28', '12:29', '12:30'] 
NOTIFICATION_INDEX = 0
EXPIRATION_DATE:datetime = datetime.now()

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

# Récuperation de la nouvelle heure.
def GetNotificationDate(index, date:datetime):
    logger.info(f"Préparation index {notification_times[index] }")
    # Obtenir la première heure de la liste de notifications
    selected_notification_time = notification_times[index]  
    logger.info(f"selected_notification_time {selected_notification_time}")
    # Extraire l'heure et les minutes
    hour, minute = map(int, selected_notification_time.split(':'))
    logger.info(f"xtraire l'heure et les minutes {hour}h et {minute} min")
    # Créer l'objet datetime pour l'expiration avec la première heure
    return date.replace(hour=hour, minute=minute, second=0, microsecond=0)

# Fonction pour gérer le nombre de jours choisi
def receive_days(update, context):
    global DAYS_ACTIVE, MODE, EXPIRATION_DATE
    logger.info(f"User entered number of days: {update.message.text}")
    
    if update.message.text.isdigit():
        DAYS_ACTIVE = int(update.message.text)
        if 0 <= DAYS_ACTIVE <= 10:
            # Date d'alerte initiale
            EXPIRATION_DATE = datetime.now() + timedelta(days=DAYS_ACTIVE)
            EXPIRATION_DATE = GetNotificationDate(0, EXPIRATION_DATE)
            MODE = "active"
            update.message.reply_text(
                    f"Mode activé pour *{DAYS_ACTIVE}* jours.\n"
                    f"Date de 1ere alerte *{EXPIRATION_DATE}*."
                    )
            logger.info(f"Notifications activated for {DAYS_ACTIVE} days.")
            logger.info(f"Date de 1ere alerte {EXPIRATION_DATE}")
            return ConversationHandler.END
        else:
            update.message.reply_text("Veuillez entrer un nombre de jours entre 1 et 10.")
    else:
        update.message.reply_text("Veuillez entrer un nombre valide (1-10).")
    return CHOOSING

# Commande pour stopper les notifications
def stop(update, context):
    global MODE, NOTIFICATION_INDEX, DAYS_ACTIVE, EXPIRATION_DATE
    MODE = "arret"
    NOTIFICATION_INDEX=0
    DAYS_ACTIVE=1
    EXPIRATION_DATE = datetime.now()
    logger.info("Stopping notifications.")
    update.message.reply_text("Mode arrêté. Vous ne recevrez plus de notifications.\n Raccourcis /start /stop /info.")
    return ConversationHandler.END

# Fonction pour envoyer un message d'info
def info_message(update, context):
    formatted_expiration_date = EXPIRATION_DATE.strftime("%A %d %B %H:%M")
    message = (
        f"Fonctionnement de l'application :\n"
        f"Mode actuel *{MODE}* {'🛑' if MODE == 'arret' else '✅'}.\n"
        f"Nombre de jours spécifié : *{DAYS_ACTIVE}* jours.\n"
        f"Alerte prévue le : *{formatted_expiration_date}*.\n"
        f"Raccourcis /start /stop /info."
    )
    send_telegram_message(update.message.chat_id, message)

# Fonction pour envoyer un message de démarrageq
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
    global NOTIFICATION_INDEX, EXPIRATION_DATE
    # Envoyer des messages si en mode "actif"
    if MODE == "active":
        current_time = datetime.now()
        #current_time = datetime.now().replace(second=0, microsecond=0)
        logger.info(f"Checking notifications at {current_time} vs {EXPIRATION_DATE}")

        # Vérifier si c'est l'heure d'envoyer un message
        if current_time >= EXPIRATION_DATE:
            logger.info(f"Oui {current_time}>={EXPIRATION_DATE}")
            # Si c'est le moment d'eenvoyer le mail
            if NOTIFICATION_INDEX == len(notification_times) - 1:
                logger.info(f"Pas de réponse et dernier index {EXPIRATION_DATE}")
                send_email(RECEIVER_EMAIL_ADDRESS, "Pas de réponse reçue", "Aucune réponse n'a été reçue concernant votre état.")
            else:
                logger.info(f"Relance normale {EXPIRATION_DATE}")
                # sinon on relance pour savoir si çà va ?
                send_telegram_message(YOUR_CHAT_ID, "Tout va bien? Répondez avec /stop si tout va bien.")
                # on change de date pour la prochaine alerte
                NOTIFICATION_INDEX = NOTIFICATION_INDEX + 1
                EXPIRATION_DATE = GetNotificationDate(NOTIFICATION_INDEX, EXPIRATION_DATE)
                logger.info(f"Prochaine relance {EXPIRATION_DATE}")
  


# Boucle principale de l'application
def main():
    logger.info("Starting the application...")
    
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
        time.sleep(CHECK_NOTIFICATION_INTERVAL)

if __name__ == '__main__':
    main()
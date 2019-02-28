import os
import sys
import logging
import requests
import json
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
from transport.data_provider import DropBoxDataProvider
from bots.mockbase import Database

dbx_token = os.environ.get('DROPBOX_TOKEN')
#telegram_token = os.environ.get('TELEGRAM_TOKEN')
telegram_token = '794555801:AAEos1HrFYUDst0orxtRZVjs_8QMIN-HsOM'

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
dbx_provider = DropBoxDataProvider(dbx_token)
db_object = Database()
ACTION, CHOICE, CHOOSE_STATION, SENT_LOCATION = range(4)

def start(bot, update):
    reply_keyboard = [['/setdata', '/getdata']]

    update.message.reply_text(
            "Hello! My name is Stella, and I will provide you with the actual information on prices of Ukrainian" \
            "gas stations.\n"
            "Simply type or choose button, what do yo want\n"
            "/setdata - send us actual photo with gas prices.\n"
            "/getdata - get information about gas prices\n"
            "If something goes wrong, simply type '/start'. If you need help, type 'help'.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

def help(bot, update):
    update.message.reply_text("Still in development./start")


#TODO: upgrade pagination
def setdata(bot, update):
    reply_keyboard = [db_object.get_companies()[:3],
                      db_object.get_companies()[3:]
                      ]
    update.message.reply_text("Please chose Fuel company from the list, \n"
                                  "or type /add_company if you can't see it",
                               reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                               one_time_keyboard=True))
    return CHOICE

def add_company(bot, update):
    update.message.reply_text("Please enter company name:")
    return ACTION

def error(bot, update, error):
    logger.warning("Update {} caused error {}".format(update, error))

def send_file_dbx(bot, update):
    update.message.reply_text("Thank you! Would you like to /start again?")
    file_id = update.message.document.file_id

    new_file = requests.get("https://api.telegram.org/bot{}/getFile?file_id={}".format(telegram_token, file_id))
    loaded_data = json.loads(new_file.text)
    file_path = loaded_data["result"]["file_path"]

    down_file = requests.get("https://api.telegram.org/file/bot{}/{}".format(telegram_token, file_path))
    dirname, basename = os.path.split(file_path)
    root_dir = os.path.splitdrive(sys.executable)[0]
    new_path = os.path.join(root_dir + os.sep, "telegram_bot", dirname, basename)
    dbx_path = "/telegram_files/" + basename

    if not os.path.exists(os.path.dirname(new_path)):
        os.makedirs(os.path.dirname(new_path))

    with open(new_path, 'wb') as output:
        output.write(down_file.content)
    dbx_provider.file_upload(new_path, dbx_path)

def cancel(bot, update):
    return ConversationHandler.END


def add_to_db(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=db_object.add_company(update.message.text))
    return sent_location(bot, update)

def sent_location(bot, update):
    location_button = KeyboardButton('Sent location', request_location=True)
    update.message.reply_text('Please, share you location so we can find nearest gas stations',
                              reply_markup=ReplyKeyboardMarkup([[location_button]],
                              one_time_keyboard=True, resize_keyboard=True))
    return SENT_LOCATION

def got_location(bot, update):
    #print(update.message.location)
    update.message.reply_text('Thanks!\n' + str(update.message.location))
    return choose_station(bot, update, update.message.location)

def choose_station(bot, update, location):
    reply_keyboard = [[db_object.get_stations()[0]],
                      [db_object.get_stations()[1]]
                      ]
    update.message.reply_text("Please chose Gas Station from the list",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                               one_time_keyboard=True))
    return CHOOSE_STATION

def send_photo(bot, update):
    update.message.reply_text("Please sent us the photo of Stella")
    return cancel(bot, update)


def main():
    updater = Updater(telegram_token)
    disp = updater.dispatcher
    disp.add_error_handler(error)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_company', add_company),
                      CommandHandler("setdata", setdata)],

        states={
            ACTION: [MessageHandler(Filters.text, add_to_db)],
            CHOICE: [CommandHandler('add_company', add_company), MessageHandler(Filters.text, sent_location)],
            SENT_LOCATION: [MessageHandler(Filters.location, got_location)],
            CHOOSE_STATION: [MessageHandler(Filters.text, send_photo)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
                    )
    disp.add_handler(conv_handler)
    disp.add_handler(CommandHandler("start", start))
    disp.add_handler(CommandHandler("help", help))
    disp.add_handler(CommandHandler("getdata", help))
    disp.add_handler(CommandHandler("chose_station", help))
    disp.add_handler(MessageHandler(Filters.document, send_file_dbx))
    disp.add_handler(MessageHandler(Filters.photo, send_file_dbx))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

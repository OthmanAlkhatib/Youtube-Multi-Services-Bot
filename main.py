from telegram.ext import CommandHandler, Updater, MessageHandler, Filters, CallbackContext, ConversationHandler, \
    CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ParseMode
import os
import logging
import sys
import getMembers
from threading import Thread
from requests import get
from pytube_video_downloader import (
    get_video_download_link,
    get_audio_download_link,
    get_time_style,
    get_srt_file,
    fetch_playlist_title,
    fetch_video_id,
)
from random import randint
from re import escape
import zipfile

TOKEN = os.getenv("TOKEN")
MODE = os.getenv("MODE")

GET_PROGRESS_TEXT = "Get My Progress"
DOWNLOAD_FROM_IDM_TEXT = "Download From IDM"
DOWNLOAD_SPECIFIC_VIDEOS = "Download Specific Videos"
ENTER_VIDEO = range(1)
SPECIFIC_VIDEO_QUALITY = 720
SINGLE_YOUTUBE_VIDEO_QUALITY = 720

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

if MODE == "dev":
    def run():
        logger.info("Start in DEV mode")
        updater.start_polling()
elif MODE == "prod":
    def run():
        logger.info("Start in PROD mode")
        updater.start_webhook(listen="0.0.0.0", port=int(os.environ.get("PORT", 5000)), url_path=TOKEN,
                              webhook_url="https://{}.herokuapp.com/{}".format("youtube-playlist-duration-bot", TOKEN))
else:
    logger.error("No mode specified")
    sys.exit(1)


def start_handler(update, context):
    username = update.message.chat.username
    if username == None:
        update.message.reply_text("Please make a Username for you Account")
        return

    in_my_channel = getMembers.in_channel(username)
    if in_my_channel :
        update.message.reply_text("Welcome, Send Me Any Youtube Video or Playlist URL to Process 🔥")
    else:
        update.message.reply_text("Sorry, You just need to join this channel https://t.me/ahsan_alhadeeth and Try Again")
        update.message.bot.sendMessage(chat_id="-980179930", text="@"+username + " == start - not in channel")
        print(username, " == not in channel")

def check_username(update: Update, context: CallbackContext):
    username = update.message.chat.username
    try:
        if username == None:
            update.message.reply_text("Please make a Username for your Account")
            return 0
        if not getMembers.in_channel(username) :
            print(username, "== not in channel")
            update.message.bot.sendMessage(chat_id="-980179930", text="@"+username + " == not in channel")
            update.message.reply_text("Sorry, You just need to join this channel https://t.me/ahsan_alhadeeth and Try Again")
            return 0
    except Exception as error:
        update.message.reply_text("Sorry, something went wrong, please try again")
        print(error)
        return 0
    print(username)
    return True

def get_playlist_duration(update: Update, context: CallbackContext):
    try:
        username = update.message.chat.username
        context.user_data["url_exist"] = 0
        playlist_url = update.message.text
        single_video_condition = "watch?v" in playlist_url or "youtu.be" in playlist_url or "/shorts/" in playlist_url or "/live/" in playlist_url
        if "playlist?list" in playlist_url:
            playlist_data = get("https://api.youtubemultidownloader.com/playlist?url=" + playlist_url).json()
            if playlist_data['status'] is False:
                raise Exception("Incorrect Playlist URL")
        elif single_video_condition:
            update.message.reply_text("Loading...")
            video_title, video_url = get_video_download_link(playlist_url, SINGLE_YOUTUBE_VIDEO_QUALITY,
                                                             is_playlist=False)
            video_title = escape(video_title)
            if video_url is False:
                raise Exception("Incorrect Youtube Video URL or Quality Error")
            else:
                update.message.reply_text(f"[{video_title}]({video_url})", parse_mode=ParseMode.MARKDOWN_V2)
                update.message.bot.sendMessage(chat_id="-980179930", text="@"+username)
                return
        else:
            raise Exception("No Youtube URL Found")

        update.message.bot.sendMessage(chat_id="-980179930", text="@"+username)
        # Save Playlist Url
        context.user_data['playlist_url'] = playlist_url
        # Save Videos Durations
        context.user_data["videos_durations"] = []
        # Save Videos URLs
        context.user_data['videos_urls'] = []
        # Save Videos Titles
        context.user_data['videos_titles'] = []

        noVideos = str(playlist_data["totalResults"])
        update.message.reply_text(noVideos + " Videos Discoverd...")

        full_duaration = 0
        for video_data in playlist_data['items']:
            full_duaration += int(video_data["duration"])
            context.user_data["videos_durations"].append(int(video_data["duration"]))
            context.user_data["videos_urls"].append(video_data["url"])
            context.user_data['videos_titles'].append(video_data["title"])

        str_duration = get_time_style(full_duaration)
        update.message.reply_text("Whole Playlist Duration : " + str_duration)

        avg_in_seconds = full_duaration / int(noVideos)
        avg_in_minutes = round(avg_in_seconds / 60, 2)
        update.message.reply_text("Average Video Length : " + str(avg_in_minutes) + " Minutes", reply_markup=buttons())
        context.user_data["url_exist"] = 1
        context.user_data["done"] = 0
        context.user_data["noVideos"] = int(noVideos)
        context.user_data["full_duration"] = full_duaration

    except Exception as error:
        update.message.reply_text("Sorry, Incorrect URL")
        print(error)


def get_playlist_thread(update: Update, context: CallbackContext):
    context.user_data['th'] = Thread(target=get_playlist_duration, args=[update, context])
    context.user_data['th'].daemon = True
    context.user_data['th'].start()


def before_get_playlist(update: Update, context: CallbackContext):
    is_user_ok = check_username(update, context)
    if not is_user_ok:
        return
    get_playlist_thread(update, context)


def buttons():
    keyboard = [[KeyboardButton(GET_PROGRESS_TEXT)], [KeyboardButton(DOWNLOAD_FROM_IDM_TEXT)],
                [KeyboardButton(DOWNLOAD_SPECIFIC_VIDEOS)]]
    return ReplyKeyboardMarkup(keyboard)


def progress_button_handler(update: Update, context: CallbackContext):
    try:
        if context.user_data["url_exist"] == 0:
            update.message.reply_text("Error, No link found")
            return ConversationHandler.END
    except:
        update.message.reply_text("Error, No link found")
        return ConversationHandler.END

    update.message.reply_text('Enter the "Number" of last video you watched : ')
    return ENTER_VIDEO


def get_progress_handler(update: Update, context: CallbackContext):
    try:
        video_number = int(update.message.text)
        if video_number < 0 or video_number > context.user_data["noVideos"]:
            raise Exception("Incorrect Video Number")
        watched = 0
        remain = context.user_data["full_duration"]
        progress = 0

        for i in range(video_number):
            watched_video_time = context.user_data["videos_durations"][i]
            watched += watched_video_time
            remain -= watched_video_time
        progress = str(round((watched * 100) / context.user_data["full_duration"], 2))

        update.message.reply_text("Watched: " + get_time_style(watched))
        update.message.reply_text("Remain: " + get_time_style(remain))
        update.message.reply_text("Your Progress: " + progress + "%")

        context.user_data["url_exist"] = 0
        return ConversationHandler.END

    except Exception as error:
        update.message.reply_text("Error, Incorrect Number")
        print(error)


def download_from_idm_button_handler(update: Update, context: CallbackContext):
    inline_keyboard = [
        [
            InlineKeyboardButton("Video MP4 360p", callback_data='playlist video mp4 360'),
            InlineKeyboardButton("Video MP4 720p", callback_data='playlist video mp4 720'),
        ],
        [
            InlineKeyboardButton("Audio M4A 128kbps", callback_data='playlist audio m4a 128'),
        ],
        [
            InlineKeyboardButton("Translation SRT English", callback_data='playlist trans str en'),
            InlineKeyboardButton("Translation SRT Arabic", callback_data='playlist trans str ar'),
        ],
        [
            InlineKeyboardButton("How to Use ?", callback_data='how_to_use')
        ],
        [
            InlineKeyboardButton("Exit", callback_data='exit')
        ],
    ]
    context.user_data["idm_message_id"] = update.message.reply_text("==== Select Video Quality ====",
                                                                    reply_markup=InlineKeyboardMarkup(inline_keyboard)
                                                                    )["message_id"]


def read_write_file(playlist_url, file_type, quality, update, context):
    if file_type == "video":
        videos_data, playlist_title = get_video_download_link(playlist_url, quality)
    elif file_type == "audio":
        videos_data, playlist_title = get_audio_download_link(playlist_url)
    file_name = file_type + " id"+str(randint(1, 1000)) + " - " + "".join(i for i in playlist_title if i not in "\/:*?<>|")
    file = open(f'{file_name}.txt', 'w')
    for video_download_url in videos_data:
        if video_download_url is False:
            continue
        file.write(video_download_url + "\n")
    file.close()

    document = open(f'{file_name}.txt', 'rb')
    print(file_name)
    return document, file_name


def download_specific_videos_button(update: Update, context: CallbackContext):
    try:
        if not context.user_data["done"]:
            inline_keyboards = []
            single_keyboard = []
            videos_titles = context.user_data["videos_titles"]
            videos_urls = context.user_data["videos_urls"]

            cnt = 1
            for video_title, video_url in zip(videos_titles, videos_urls):
                single_keyboard.append([InlineKeyboardButton(video_title, callback_data=video_url)])
                if cnt % 50 == 0:
                    inline_keyboards.append(single_keyboard.copy())
                    single_keyboard.clear()
                cnt += 1
            single_keyboard.append([InlineKeyboardButton("=== Done ===", callback_data='done')])
            inline_keyboards.append(single_keyboard)

            update.message.reply_text(f"=== NOTE : All Videos Are MP4 {str(SPECIFIC_VIDEO_QUALITY)}p ===")
            context.user_data["long_inline_keyboards"] = []
            for keyboard in inline_keyboards:
                try:
                    context.user_data["long_inline_keyboards"].append(
                        update.message.reply_text("Choose Your Videos : ", reply_markup=InlineKeyboardMarkup(keyboard))[
                            "message_id"])
                except Exception as error:
                    update.message.reply_text("Sorry, Can not use this option for this playlist.")
        else:
            update.message.reply_text("Error, No link found")
    except Exception as error:
        update.message.reply_text("Error, No link found")
        print(error)


def download_specific_videos_handler(update, context, video_title, video_url):
    try:
        escaped_title = escape(video_title)
        context.bot.send_message(update.effective_chat.id,
                                 f"[{escaped_title}]({get_video_download_link(video_url, SPECIFIC_VIDEO_QUALITY, just_url=True, is_playlist=False)})",
                                 parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as error:
        print(error)
        context.bot.sendMessage(update.effective_chat.id, "Sorry, Can Not Download This Video")


def callback_query_handler(update: Update, context: CallbackContext):
    query = update.callback_query.data
    update.callback_query.answer()

    try:
        if "watch?v" in query:
            context.bot.sendMessage(update.effective_chat.id, "Loading Video Data, Wait a Second..")
            url = query
            url_index = context.user_data["videos_urls"].index(url)
            title = context.user_data["videos_titles"][url_index]
            download_specific_videos_handler(update, context, title, url)
            return
        elif "done" in query:
            for message_id in context.user_data['long_inline_keyboards']:
                context.bot.editMessageReplyMarkup(update.effective_chat.id,
                                                   message_id=message_id,
                                                   reply_markup=None)
            context.user_data["done"] = 1
            return
    except Exception as error:
        context.bot.sendMessage(update.effective_chat.id, "Error, Something went wrong, Resend your URL again.")
        print(error)
        return

    if "how_to_use" in query:
        context.bot.sendMessage(update.effective_chat.id, """
    Steps : 
1_ Copy whole text in data.txt file.

2_ Go to your IDM in your (PC/Mobile) and find "Download from clipboard" option.

3_ Choose Your videos and start DOWNLOAD :)
    """)
        context.bot.sendMessage(update.effective_chat.id, """
    For PC :
Open You Internet Download Manager Program and Select the Option Like the Photo Below.
        """)
        context.bot.sendPhoto(update.effective_chat.id, "https://t.me/mstoda3/255")
        context.bot.sendMessage(update.effective_chat.id, """
    For Mobile :
Open Your IDM Application and Select the Option Like the Photo Below.
        """)
        context.bot.sendPhoto(update.effective_chat.id, "https://t.me/mstoda3/256")
        return

    if "exit" in query:
        try:
            context.bot.editMessageReplyMarkup(update.effective_chat.id,
                                               message_id=context.user_data['idm_message_id'],
                                               reply_markup=None)
            if context.user_data.get('playlist_url', None): del context.user_data["playlist_url"]
            return
        except Exception as error :
            context.bot.sendMessage(update.effective_chat.id, "Error, Something Went Wrong, Please Try Again.")
            print(error)
            return

    url_type, file_type, file_ext, quality = query.split(" ")
    if url_type == "playlist":
        if file_type == "video" or file_type == "audio":
            try:
                quality = int(quality)
                playlist_url = context.user_data['playlist_url']
            except Exception as error:
                context.bot.sendMessage(update.effective_chat.id, "Error, No link found, Resend URL again.")
                return

            context.bot.sendMessage(update.effective_chat.id, "Loading Data.. (This may take some time)")
            try:
                document, filename = read_write_file(playlist_url, file_type, quality, update, context)
                context.bot.sendDocument(update.effective_chat.id, document)
                document.close()
                os.remove(filename + ".txt")
            except Exception as error:
                context.bot.sendMessage(update.effective_chat.id, "Error, Something went wrong")
                print(error)
                return
        elif file_type == "trans":
            lang = quality
            try:
                playlist_url = context.user_data['playlist_url']
            except Exception as error:
                context.bot.sendMessage(update.effective_chat.id, "Error, No link found, Resend URL again.")
                print(error)
                return

            context.bot.sendMessage(update.effective_chat.id, "Loading Data.. (This may take some time)")
            file_names = []
            for video_cnt in range(len(context.user_data["videos_urls"])):
                try:
                    video_url = context.user_data["videos_urls"][video_cnt]
                    video_title = context.user_data["videos_titles"][video_cnt]
                    video_id = video_url.split("?v=")[1]
                    file_name = "".join(i for i in video_title if i not in "\/:*?<>|")
                    is_file_created = get_srt_file(video_id, file_name, lang=lang)
                    if is_file_created: file_names.append(file_name + ".srt")
                except Exception as error:
                    print("++ Line 391 ++")
                    print(error)
            try:
                if not file_names:
                    context.bot.sendMessage(update.effective_chat.id, "Sorry, there is no translations for this language")
                    return
                playlist_title = fetch_playlist_title(playlist_url)
                zip_file_name = "id" + str(randint(1, 10)) + " - " + "".join(i for i in playlist_title if i not in "\/:*?<>|")
                with zipfile.ZipFile(f'{zip_file_name}.zip', 'w', zipfile.ZIP_DEFLATED) as myzip:
                    for file_name in file_names:
                        myzip.write(file_name)
                        os.remove(file_name)
                read_zip_file = open(f"{zip_file_name}.zip", "rb")
                context.bot.sendDocument(update.effective_chat.id, read_zip_file)
                read_zip_file.close()
                os.remove(f'{zip_file_name}.zip')
            except Exception as error:
                print("==== Can Not Create Zip File ====")
                print(error)
                context.bot.sendMessage(update.effective_chat.id,
                                        "Sorry, Something went wrong while creating your file.")

    elif url_type == "video":
        pass


def call_back_thread(update: Update, context: CallbackContext):
    th = Thread(target=callback_query_handler, args=[update, context])
    th.daemon = True
    th.start()


if __name__ == "__main__":
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(CommandHandler("start", start_handler))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(GET_PROGRESS_TEXT), progress_button_handler)],
        states={
            ENTER_VIDEO: [MessageHandler(Filters.all, get_progress_handler)],
        },
        fallbacks=[]
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(DOWNLOAD_FROM_IDM_TEXT), download_from_idm_button_handler))
    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(DOWNLOAD_SPECIFIC_VIDEOS), download_specific_videos_button))
    updater.dispatcher.add_handler(CallbackQueryHandler(call_back_thread))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, before_get_playlist))

    run()

import os
import json
import telebot
import gspread
import threading
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv

# Library BARU, bukan google.generativeai lagi
from google import genai
from google.genai import types

load_dotenv()

TELEGRAM_TOKEN = os.getenv("1653751429:AAEFQqxCiDu8wXgImbrHbJD3Om8hsxfQaEk")
GEMINI_KEY = os.getenv("AQ.Ab8RN6Jgv1KZQKSWEO_mZOmkA8whTLpRVgPCcoefzvSlmzN2rQ")
SHEET_NAME = os.getenv("SHEET_NAME", "Database Boto")

# Cek token biar errornya jelas, ga crash aneh-aneh
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN kosong! Cek Variables di Railway!")
    exit()
if not GEMINI_KEY:
    print("ERROR: GEMINI_API_KEY kosong! Cek Variables di Railway!")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Client Gemini baru
client = genai.Client(api_key=GEMINI_KEY)
MODEL_NAME = "gemini-2.5-flash-lite"

def tanya_gemini(pertanyaan):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=pertanyaan,
        config=types.GenerateContentConfig(
            max_output_tokens=600,
            temperature=0.7,
            top_p=0.9,
        )
    )
    return response.text

# --- SHEETS ---
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    try:
        if creds_json:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client_gs = gspread.authorize(creds)
        return client_gs.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"Gagal konek Sheet: {e}")
        return None

sheet = get_sheet()
print("Bot SATSET jalan...")

def simpen_history(user_id, username, nama, pertanyaan, jawaban):
    if not sheet:
        return
    try:
        tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([tanggal, str(user_id), username, nama, pertanyaan, jawaban])
    except Exception as e:
        print(f"Gagal simpen: {e}")

def simpen_background(user_id, username, nama, pertanyaan, jawaban):
    threading.Thread(target=simpen_history, args=(user_id, username, nama, pertanyaan, jawaban), daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    nama = message.from_user.first_name
    bot.reply_to(message, f"Halo {nama}! 👋\nTanya aja, gua jawab satset.")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_chat(message):
    user_id = message.from_user.id
    username = message.from_user.username or "-"
    nama = message.from_user.first_name or "User"
    pertanyaan = message.text
    try:
        jawaban = tanya_gemini(pertanyaan)
        bot.reply_to(message, jawaban)
        simpen_background(user_id, username, nama, pertanyaan, jawaban)
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Waduh error bro, coba lagi bentar ya 🙏")

if __name__ == "__main__":
    print("Bot 2.5-flash-lite SATSET jalan...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)

import asyncio
import requests
from collections import deque, Counter
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import random
from flask import Flask
import threading
import os

# Inisialisasi Flask
app = Flask(__name__)

# Kode bot Anda tetap sama
class Config:
    TOKEN = "8142597643:AAFNDUq27fpQeMhbQHGxCo3R7SUPre8DN3w"
    CHAT_IDS = [7777353888]
    API_URL = "https://didihub20.com/api/main/lottery/rounds?page=1&count=20&type=3"
    KOMPEN_TABLE = ["x1", "x3", "x6", "x16", "x32", "x8", "x16", "x35", "x80", "x170", "x400", "x800", "x1800", "x5000"]
    PREDICTION_PATTERN = ["B", "K", "B", "B", "K", "K"]
    GROUP_LINKS = {
        "-1002449267243": {
            "register": "https://www.didihub.net",
            "join": "t.me/YASSATRADERPRO"
        },
        "default": {
            "register": "https://didihub.link/register?spreadCode=BLQZ3",
            "join": "https://didihub.link/login?spreadCode=BLQZ3"
        }
    }

class BotState:
    def __init__(self):
        self.last_sent_period = None
        self.current_bet_index = 0
        self.current_bet_amount = Config.KOMPEN_TABLE[0]
        self.pattern_index = 0
        self.loss_streak = 0
        self.history = deque(maxlen=20)

class APIService:
    @staticmethod
    def get_lottery_data():
        try:
            response = requests.get(Config.API_URL)
            return response.json().get("items", []) if response.status_code == 200 else []
        except Exception:
            return []

class PredictionLogic:
    @staticmethod
    def check_win_loss(prediction, last_result):
        result_type = "K" if 0 <= last_result <= 4 else "B"
        status = "✅" if prediction == result_type else "☑️"
        return status, last_result, result_type

    @staticmethod
    def get_most_frequent_trend(data):
        numbers = [item["number"] for item in data]
        counter = Counter(numbers)
        if not counter:
            return "B"
        big_count = sum(count for num, count in counter.items() if num >= 5)
        small_count = sum(count for num, count in counter.items() if num <= 4)
        return "B" if big_count >= small_count else "K"

    @staticmethod
    def get_next_prediction(state, data):
        if state.loss_streak >= 1:
            return PredictionLogic.get_most_frequent_trend(data)
        prediction = Config.PREDICTION_PATTERN[state.pattern_index]
        state.pattern_index = (state.pattern_index + 1) % len(Config.PREDICTION_PATTERN)
        return prediction

    @staticmethod
    def update_bet(state, status):
        if status == "✅":
            state.current_bet_index = 0
            state.loss_streak = 0
        else:
            state.current_bet_index = min(state.current_bet_index + 1, len(Config.KOMPEN_TABLE) - 1)
            state.loss_streak += 1
        state.current_bet_amount = Config.KOMPEN_TABLE[state.current_bet_index]

class TelegramService:
    def __init__(self):
        self.bot = Bot(token=Config.TOKEN)

    async def send_message(self, chat_id, message, register_url, join_url):
        keyboard = [
            [InlineKeyboardButton("🔗 DAFTAR", url=register_url)],
            [InlineKeyboardButton("🔗 LOGIN", url=join_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception:
            pass

class LotteryBot:
    def __init__(self):
        self.state = BotState()
        self.api_service = APIService()
        self.prediction_logic = PredictionLogic()
        self.telegram_service = TelegramService()

    def _format_history_message(self, short_last_period, short_next_period, prediction, random_percentage, bet_amount):
        header = (
            "\n<b>🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥</b>\n"
            "<b>🚦         WINGO🚥CEPAT         🚦</b>\n"
            "<b>🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥</b>\n"
            "<b>🚦NO 🚦🔮🚦HASIL🚦W/L🚦 BET 🚦</b>\n"
            "<b>🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥🚥</b>\n"
        )
        footer = (
            f"\n\n<b>#Riwayat_No{short_last_period}</b>"
            f"\n📢 <b>Prediksi Server: WINGO CEPAT</b>"
            f"\n🎯 <b>Periode: {short_next_period}</b>"
            f"\n🔮 <b>Prediksi: {prediction} ({random_percentage:.2%})</b>"
            f"\n💰 <b>Taruhan: 1000 {bet_amount}</b>"
        )
        return header + "\n".join(self.state.history) + footer

    async def run(self):
        while True:
            data = self.api_service.get_lottery_data()
            if not data:
                await asyncio.sleep(5)
                continue

            last_period = int(data[0]["period"])
            last_result = data[0]["number"]
            next_period = last_period + 1
            short_last_period = str(last_period)[-3:]
            short_next_period = str(next_period)[-3:]

            if last_period != self.state.last_sent_period:
                prediction = self.prediction_logic.get_next_prediction(self.state, data)
                status, result_number, result_type = self.prediction_logic.check_win_loss(prediction, last_result)
                bet_amount = self.state.current_bet_amount

                self.prediction_logic.update_bet(self.state, status)
                random_percentage = random.uniform(0.50, 0.99)

                self.state.history.append(
                    f"<b>🚦{short_last_period}🚦 {prediction} 🚦 {result_type} {result_number} 🚦 {status} 🚦1000🚦{bet_amount}</b>"
                )

                history_message = self._format_history_message(
                    short_last_period, short_next_period, prediction, random_percentage, bet_amount
                )

                for chat_id in Config.CHAT_IDS:
                    links = Config.GROUP_LINKS.get(str(chat_id), Config.GROUP_LINKS["default"])
                    await self.telegram_service.send_message(
                        chat_id=chat_id,
                        message=history_message,
                        register_url=links["register"],
                        join_url=links["join"]
                    )

                self.state.last_sent_period = last_period

            await asyncio.sleep(5)

# Endpoint HTTP sederhana untuk menjaga aplikasi tetap hidup
@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

# Fungsi untuk menjalankan bot di thread terpisah
def run_bot():
    bot = LotteryBot()
    asyncio.run(bot.run())

# Mulai bot di thread terpisah saat aplikasi Flask berjalan
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

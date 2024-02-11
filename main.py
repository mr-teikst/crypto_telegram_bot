import logging
import math
from typing import Final, List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, \
    filters, MessageHandler
from APIs.crypto_apis import get_crypto_list, get_crypto_price, get_price_range
import os
from datetime import datetime, date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

BOT_TOKEN: Final = "6326700219:AAH3pVVbe9DCjFFnKv8r3INPTCe95NeqlfQ"

# logger config
logging.basicConfig(format='%(levelname)s - (%(asctime)s) - %(message)s - (Line: %(lineno)d) - [%(filename)s]',
                    datefmt='%H:%M:%S',
                    encoding='utf-8',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class BigManager:
    # states:
    s_home = 0

    s_list = 1
    s_normal_add = 6
    s_normal_delete = 7

    s_favorite = 2
    s_favorite_add = 8
    s_favorite_delete = 9

    s_price = 3
    # s_price_show = 10

    s_plot = 4
    s_compare = 5

    def __init__(self):
        self.l_db: pd.DataFrame
        self.h_db: pd.DataFrame
        self.d_db: pd.DataFrame
        self.user_db_filename = "user_db_address.txt"
        if os.path.exists(self.user_db_filename):
            # Open the existing file
            with open(self.user_db_filename, 'r') as file:
                self.user_db = [line.strip() for line in file.readlines()]
        else:
            self.user_db = []

    async def cleaner(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.user_data['delete_message']) != 0:
            for m_id in context.user_data['delete_message']:
                try:
                    await context.bot.delete_message(update.effective_chat.id, m_id)
                except:
                    pass
            context.user_data['delete_message'] = []

    def get_crypto(self, crypto):
        if (crypto in self.l_db["name"].values) or (crypto in self.l_db["symbol"].values):
            name_row = self.l_db[self.l_db['name'] == crypto]
            symbol_row = self.l_db[self.l_db['symbol'] == crypto]
            if not name_row.empty:
                return name_row["symbol"][name_row.index[0]]
            else:
                return symbol_row["symbol"][symbol_row.index[0]]
        else:
            return False

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["delete_message"]: list = []
        if str(update.effective_user.id) not in self.user_db:
            self.user_db.append(update.effective_user.id)
            with open(self.user_db_filename, 'w') as file:
                for item in self.user_db:
                    file.write(str(item) + "\n")

            self.l_db = pd.DataFrame(columns=["name", "symbol", "favorite"])
            self.l_db.to_csv(f"DBs\l_db_{update.effective_user.id}.csv")

            self.h_db = pd.DataFrame(columns=["id", "price", "date", "count"])
            self.h_db.to_csv(f"DBs\h_db_{update.effective_user.id}.csv")

            self.d_db = pd.DataFrame(columns=["id", "date", "min", "max"])
            self.d_db.to_csv(f"DBs\d_db_{update.effective_user.id}.csv")
        else:
            self.l_db = pd.read_csv(f"DBs\l_db_{update.effective_user.id}.csv")
            self.h_db = pd.read_csv(f"DBs\h_db_{update.effective_user.id}.csv")
            self.d_db = pd.read_csv(f"DBs\d_db_{update.effective_user.id}.csv")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="خوش آمدید!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="Home", callback_data="home")]
                ]
            )
        )

        return self.s_home

    async def home_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self.cleaner(update, context)

        await query.edit_message_text(
            text="خانه:" "\n"
                 "چیکار کنیم؟",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="لیست کل ارزها", callback_data="list")],
                    [InlineKeyboardButton(text="لیست مورد علاقه ها", callback_data="favorite_list")],
                    [InlineKeyboardButton(text="قیمت چند؟", callback_data="get_price")],
                    [InlineKeyboardButton(text="نشونش بده!", callback_data="plot")],
                    [InlineKeyboardButton(text="مقایسه کن!", callback_data="compare")],
                ]
            )
        )
        return self.s_home

    async def list_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self.cleaner(update, context)

        if not self.l_db.empty:
            text = "این ارزهاییه ک اضافه کردی:" "\n"
            for i, row in self.l_db.iterrows():
                text += f"Name: {row['name']} | symbol: {row['symbol']} \n"
        else:
            text = "شما رمز ندارید، لطفا یدونه اضافه کنید"

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="اضافه کردن", callback_data="normal_add"),
                     InlineKeyboardButton(text="پاک کردن", callback_data="normal_delete")],

                    [InlineKeyboardButton(text="خونه", callback_data="home")],

                ]
            )
        )
        return self.s_list

    async def normal_add_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="لطفا اسم(یا نماد) یک(یا چند) رمزارز را به فرمت زیر ارسال کنید " "\n"
                 "تکی:" "\n"
                 "btc" "\n"
                 "چند تایی:" "\n"
                 "btc&tether&usdc&...",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="بازگشت", callback_data="list")],
                    [InlineKeyboardButton(text="خانه", callback_data="home")]
                ]
            )
        )
        return self.s_normal_add

    async def normal_add_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cryptos = update.effective_message.text.lower().split("&")
        for crypto in cryptos:
            if (crypto not in self.l_db["name"].values) and (crypto not in self.l_db["symbol"].values):
                name, symbol = get_crypto_list(crypto)
                if name and symbol:
                    new_row = {"name": name, "symbol": symbol, "favorite": False}
                    self.l_db = self.l_db._append(new_row, ignore_index=True)
                    self.l_db.to_csv(f"DBs\l_db_{update.effective_user.id}.csv")
                    message = await context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=f"{crypto}" " "
                             "به لیست اضافه شد",
                        reply_to_message_id=update.effective_message.id,
                    )
                else:
                    message = await context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=f"{crypto}" " "
                             "چنین ارزی وجود ندارد",
                        reply_to_message_id=update.effective_message.id,
                    )
            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{crypto}" " "
                         "از قبل در لیست وجود دارد",
                    reply_to_message_id=update.effective_message.id,
                )
            context.user_data["delete_message"].append(message.id)
        context.user_data["delete_message"].append(update.effective_message.id)
        return self.s_normal_add

    async def normal_delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="لطفا اسم(یا نماد) یک(یا چند) رمزارز را برای حذف کردن به فرمت زیر ارسال کنید " "\n"
                 "تکی:" "\n"
                 "btc" "\n"
                 "چند تایی:" "\n"
                 "btc&tether&usdc&...",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="بازگشت", callback_data="list")],
                    [InlineKeyboardButton(text="خانه", callback_data="home")]
                ]
            )
        )
        return self.s_normal_delete

    async def normal_delete_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cryptos = update.effective_message.text.lower().split("&")
        drop_list = []
        for crypto in cryptos:
            m_crypto = crypto
            crypto = self.get_crypto(crypto)
            if crypto:
                row_to_delete = self.l_db[self.l_db['symbol'] == crypto]
                drop_list.append(row_to_delete.index[0])

                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{crypto}" " "
                         "از لیست حذف شد",
                    reply_to_message_id=update.effective_message.id,
                )
            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{m_crypto}" " "
                         "در لیست وجود ندارد",
                    reply_to_message_id=update.effective_message.id,
                )
            context.user_data["delete_message"].append(message.id)
        context.user_data["delete_message"].append(update.effective_message.id)
        self.l_db = self.l_db.drop(drop_list)
        self.l_db.to_csv(f"DBs\l_db_{update.effective_user.id}.csv")
        return self.s_normal_delete

    async def favorite_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self.cleaner(update, context)
        df = self.l_db[self.l_db["favorite"] == True]
        if not df.empty:
            text = "این ارزهاییه ک مورد علاقتن:" "\n"
            for i, row in self.l_db.iterrows():
                if row["favorite"]:
                    text += f"Name: {row['name']} | symbol: {row['symbol']} \n"
        else:
            text = "شما رمز ندارید، لطفا یدونه اضافه کنید"

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="اضافه کردن", callback_data="favorite_add"),
                     InlineKeyboardButton(text="پاک کردن", callback_data="favorite_delete")],

                    [InlineKeyboardButton(text="خونه", callback_data="home")],

                ]
            )
        )
        return self.s_favorite

    async def favorite_add_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="لطفا اسم(یا نماد) یک(یا چند) رمزارز را به فرمت زیر ارسال کنید " "\n"
                 "تکی:" "\n"
                 "btc" "\n"
                 "چند تایی:" "\n"
                 "btc&tether&usdc&...",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="بازگشت", callback_data="favorite")],
                    [InlineKeyboardButton(text="خانه", callback_data="home")]
                ]
            )
        )
        return self.s_favorite_add

    async def favorite_add_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cryptos = update.effective_message.text.lower().split("&")
        for crypto in cryptos:
            m_crypto = crypto
            crypto = self.get_crypto(crypto)
            if crypto:
                row = self.l_db[self.l_db["symbol"] == crypto]
                if not row["favorite"][row.index[0]]:
                    self.l_db.loc[self.l_db["symbol"] == crypto, "favorite"] = True
                    self.l_db.to_csv(f"DBs\l_db_{update.effective_user.id}.csv")
                    message = await context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=f"{crypto}" " "
                             "به مورد علاقه ها اضافه شد",
                        reply_to_message_id=update.effective_message.id,
                    )
                else:
                    message = await context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=f"{crypto}" " "
                             "از قبل مورد علاقه بوده",
                        reply_to_message_id=update.effective_message.id,
                    )

            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{m_crypto}" " "
                         "در لیست وجود ندارد",
                    reply_to_message_id=update.effective_message.id,
                )
            context.user_data["delete_message"].append(message.id)
        context.user_data["delete_message"].append(update.effective_message.id)
        return self.s_favorite_add

    async def favorite_delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="لطفا اسم(یا نماد) یک(یا چند) رمزارز را برای حذف از مورد علاقه ها به فرمت زیر ارسال کنید " "\n"
                 "تکی:" "\n"
                 "btc" "\n"
                 "چند تایی:" "\n"
                 "btc&tether&usdc&...",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text="بازگشت", callback_data="favorite")],
                    [InlineKeyboardButton(text="خانه", callback_data="home")]
                ]
            )
        )
        return self.s_favorite_delete

    async def favorite_delete_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cryptos = update.effective_message.text.lower().split("&")
        for crypto in cryptos:
            m_crypto = crypto
            crypto = self.get_crypto(crypto)
            if crypto:
                row = self.l_db[self.l_db["symbol"] == crypto]
                if row["favorite"][row.index[0]]:
                    self.l_db.loc[self.l_db["symbol"] == crypto, "favorite"] = False
                    self.l_db.to_csv(f"DBs\l_db_{update.effective_user.id}.csv")
                    message = await context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=f"{crypto}" " "
                             "از مورد علاقه ها حذف شد",
                        reply_to_message_id=update.effective_message.id,
                    )
                else:
                    message = await context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=f"{crypto}" " "
                             "از قبل مورد علاقه نبوده",
                        reply_to_message_id=update.effective_message.id,
                    )

            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{m_crypto}" " "
                         "در لیست وجود ندارد",
                    reply_to_message_id=update.effective_message.id,
                )
            context.user_data["delete_message"].append(message.id)
        context.user_data["delete_message"].append(update.effective_message.id)
        return self.s_favorite_delete

    async def price_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cleaner(update, context)
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text="لطفا اسم(یا نماد) یک(یا چند) رمزارز را به فرمت زیر ارسال کنید " "\n"
                     "تکی:" "\n"
                     "btc" "\n"
                     "چند تایی:" "\n"
                     "btc&tether&usdc&...",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(text="خانه", callback_data="home")],
                        [InlineKeyboardButton(text="دوباره", callback_data="get_price")],
                    ]
                )
            )
        except:
            pass
        return self.s_price

    async def price_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cryptos = update.effective_message.text.lower().split("&")
        cryptos.sort()
        for crypto in cryptos:
            m_crypto = crypto
            crypto = self.get_crypto(crypto)
            if crypto:
                price = get_crypto_price(crypto)
                date_to_show = datetime.now()
                date = datetime.now().strftime("%Y_%m_%d %H")
                if self.h_db[self.h_db["date"] == date].empty:
                    new_row = {"id": crypto, "price": price, "date": date, "count": 1}
                    self.h_db = self.h_db._append(new_row, ignore_index=True)
                    self.h_db.to_csv(f"DBs\h_db_{update.effective_user.id}.csv")
                else:
                    row = self.h_db[self.h_db["date"] == date]
                    last_price = row["price"][row.index[0]]
                    count = row["count"][row.index[0]]
                    new_price = (last_price * count + price) / (count + 1)
                    self.h_db.loc[self.h_db["date"] == date, "price"] = new_price
                    self.h_db.loc[self.h_db["date"] == date, "count"] = count + 1
                    self.h_db.to_csv(f"DBs\h_db_{update.effective_user.id}.csv")

                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{crypto} -> Price(usd): {price}, Date: {date_to_show}",
                    reply_to_message_id=update.effective_message.id,
                )
            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{m_crypto}" " "
                         "در لیست وجود ندارد",
                    reply_to_message_id=update.effective_message.id,
                )

            context.user_data["delete_message"].append(message.id)

            context.user_data["delete_message"].append(update.effective_message.id)
        return self.s_price

    async def plot_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cleaner(update, context)
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text="لطفا اسم(یا نماد) یک رمزارز را برای نمایش (از دیتاهای داخلی جمع آوری شده در بخش قیمت چند؟) به فرمت زیر ارسال کنید " "\n"
                     "تکی:" "\n"
                     "btc" "\n",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(text="خانه", callback_data="home")],
                        [InlineKeyboardButton(text="دوباره", callback_data="plot")],
                    ]
                )
            )
        except:
            pass
        return self.s_plot

    def simplot(self, df, crypto, update):
        x = np.array(df["date"])
        y = np.array(df["price"])

        plt.plot(x, y, color="black", marker="o", mec="blue", mfc="blue")
        plt.title(f"{crypto.upper()} Price(usd)/Time(hour)")
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.grid(axis="y")
        plt.savefig(f'plots\plot_{update.effective_user.id}.png')
        return f'plots\plot_{update.effective_user.id}.png'

    async def plot_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        crypto = update.effective_message.text.lower()
        m_crypto = crypto
        crypto = self.get_crypto(crypto)
        if crypto:
            rows = self.h_db[self.h_db["id"] == crypto]
            if not rows.empty:
                photo_path = self.simplot(rows, crypto, update)
                message = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=open(photo_path, 'rb'),
                    caption=f"اینم نمودار:" "\n"
                            f"{crypto}",
                )
            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{crypto}" "\n"
                         "برای این ارز اطلاعاتی جمع آوری نشده است",
                    reply_to_message_id=update.effective_message.id,
                )
        else:
            message = await context.bot.sendMessage(
                chat_id=update.effective_chat.id,
                text=f"{m_crypto}" "\n"
                     "در لیست وجود ندارد",
                reply_to_message_id=update.effective_message.id,
            )
        context.user_data["delete_message"].append(update.effective_message.id)
        context.user_data["delete_message"].append(message.id)
        return self.s_plot

    async def compare_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cleaner(update, context)
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text="لطفا اسم(یا نماد) چند(نهایتا 6) رمزارز را برای مقایسه و نمایش در n روز گذشته(نهایتا 30) به فرمت زیر ارسال کنید " "\n"
                     "چند تایی:" "\n"
                     "btc&usdt&link&... (max:6)" "\n"
                     "7 (max:30)" "\n",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(text="خانه", callback_data="home")],
                        [InlineKeyboardButton(text="دوباره", callback_data="compare")],
                    ]
                )
            )
        except:
            pass
        return self.s_compare

    def get_days(self, num: int) -> list:
        today = date.today()
        last_n_days = []

        for i in range(num):
            delta = timedelta(days=i)
            day = today - delta
            day = day.strftime('%Y-%m-%d')
            last_n_days.append(day)

        last_n_days = last_n_days[::-1]
        return last_n_days

    def compare_plot(self, crypto, dates, update):
        rows = self.d_db[self.d_db["id"] == crypto]
        rows = rows[rows["date"].isin(dates)]

        x = np.array(rows["date"])
        y_min = np.array(rows["min"])
        y_max = np.array(rows["max"])

        self.plt.fill_between(x, y_max, y_min, alpha=0.3)
        self.plt.plot(x, (y_max + y_min) / 2, color='black', linewidth=2.5)
        self.plt.xlabel('Time')
        self.plt.ylabel('price(usd)')
        self.plt.title(f'{crypto} plot')

        self.plt.savefig(f'plots\compare_plot_{update.effective_user.id}.png')
        return f'plots\compare_plot_{update.effective_user.id}.png'

    def suggestion(self, cryptos, dates):
        outcome = dict([])
        df = self.d_db.copy()
        df = df.sort_values(by='date')
        df["price"] = df["min"] + df["max"] / 2
        for crypto in cryptos:
            crypto = self.get_crypto(crypto)
            if crypto:
                clean_df = df[df["id"] == crypto]
                clean_df = clean_df[clean_df["date"].isin(dates)]
                _ = 0
                prices = clean_df["price"].values
                for index in range(len(clean_df['price']) - 2):
                    _ += (prices[index + 1] - prices[index]) / prices[index] * 100
                outcome[crypto] = _
        if outcome:
            return outcome
        else:
            return None

    async def compare_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cryptos, days_num = update.effective_message.text.lower().split("\n")
        cryptos = cryptos.split("&")
        dates = self.get_days(int(days_num))
        photo_path = None
        message_ = await context.bot.sendMessage(
            chat_id=update.effective_chat.id,
            text=f"در حال پردازش و دریافت اطلاعات (ممکن است کمی طول بکشد)",
            reply_to_message_id=update.effective_message.id,
        )
        for i, crypto in enumerate(cryptos):
            m_crypto = crypto
            crypto = self.get_crypto(crypto)
            if crypto:
                rows = self.d_db[self.d_db["id"] == crypto]
                clean_dates = dates.copy()
                existed_date_list = []
                for index, date in enumerate(dates):
                    if date in rows["date"].values:
                        existed_date_list.append(index)
                for index in sorted(existed_date_list, reverse=True):
                    del clean_dates[index]

                if clean_dates:
                    new_prices = get_price_range(crypto, clean_dates)
                    for date in clean_dates:
                        new_row = {"id": crypto, "date": date,
                                   "min": new_prices[date]["min"],
                                   "max": new_prices[date]["max"],
                                   }
                        self.d_db = self.d_db._append(new_row, ignore_index=True)
                        self.d_db.to_csv(f"DBs\d_db_{update.effective_user.id}.csv")

                rows = self.d_db[self.d_db["id"] == crypto]

                self.plt = plt
                self.plt.rcParams['figure.figsize'] = (25, 22)  # Width = 12 inches, Height = 8 inches
                self.plt.subplot(math.ceil(len(cryptos) / 2), 2, i + 1)

                photo_path = self.compare_plot(crypto, dates, update)

            else:
                message = await context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    text=f"{m_crypto}" "\n"
                         "در لیست وجود ندارد",
                    reply_to_message_id=update.effective_message.id,
                )
        if photo_path:
            message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(photo_path, 'rb'),
                caption=f"اینم نمودار مقایسه:" "\n",
            )

        suggestions_dict = self.suggestion(cryptos, dates)
        if suggestions_dict:
            text = f"درصد تغییرات" ":\n"
            for key in suggestions_dict:
                text += f"{key}: {suggestions_dict[key]:.4f}% \n"

            suggest = max(suggestions_dict, key=suggestions_dict.get)
            text += "بهترین رمزی که می شد خرید" ":\n" \
                    f"{suggest} -> {suggestions_dict[suggest]:.4f}%"

            message_3 = await context.bot.sendMessage(
                chat_id=update.effective_chat.id,
                text=text,
                reply_to_message_id=update.effective_message.id,
            )
            context.user_data["delete_message"].append(message_3.id)

        context.user_data["delete_message"].append(message.id)
        context.user_data["delete_message"].append(message_.id)
        context.user_data["delete_message"].append(update.effective_message.id)

        return self.s_compare


if __name__ == "__main__":
    logger.warning("bot starting ...")
    bm = BigManager()
    bot = ApplicationBuilder().token(BOT_TOKEN).build()
    bot.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("start", bm.start_handler)],
            states={
                bm.s_home: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.list_handler, pattern="list"),
                    CallbackQueryHandler(bm.favorite_handler, pattern="favorite_list"),
                    CallbackQueryHandler(bm.price_handler, pattern="get_price"),
                    CallbackQueryHandler(bm.plot_handler, pattern="plot"),
                    CallbackQueryHandler(bm.compare_handler, pattern="compare")
                ],

                bm.s_list: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.normal_add_handler, pattern="normal_add"),
                    CallbackQueryHandler(bm.normal_delete_handler, pattern="normal_delete"),
                ],
                bm.s_normal_add: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.list_handler, pattern="list"),
                    MessageHandler(filters.TEXT, bm.normal_add_message_handler),
                ],
                bm.s_normal_delete: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.list_handler, pattern="list"),
                    MessageHandler(filters.TEXT, bm.normal_delete_message_handler),
                ],

                bm.s_favorite: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.favorite_add_handler, pattern="favorite_add"),
                    CallbackQueryHandler(bm.favorite_delete_handler, pattern="favorite_delete"),
                ],
                bm.s_favorite_add: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.favorite_handler, pattern="favorite"),
                    MessageHandler(filters.TEXT, bm.favorite_add_message_handler),
                ],
                bm.s_favorite_delete: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.favorite_handler, pattern="favorite"),
                    MessageHandler(filters.TEXT, bm.favorite_delete_message_handler),
                ],

                bm.s_price: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.price_handler, pattern="get_price"),
                    MessageHandler(filters.TEXT, bm.price_message_handler),
                ],

                bm.s_plot: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.plot_handler, pattern="plot"),
                    MessageHandler(filters.TEXT, bm.plot_message_handler),
                ],
                bm.s_compare: [
                    CallbackQueryHandler(bm.home_handler, pattern="home"),
                    CallbackQueryHandler(bm.compare_handler, pattern="compare"),
                    MessageHandler(filters.TEXT, bm.compare_message_handler),
                ],
            },
            fallbacks=[],
            allow_reentry=True,
        )
    )

    logger.warning("polling ...")
    bot.run_polling()

import pandas as pd
import asyncio
from telegram import Bot
from datetime import datetime
from src.config import BOT_TOKEN, CHANNEL_USERNAME, get_today_processed_csv

def format_message(row):
    return f"""🌐 *Город:* {row.get('location', '---')}
📅 *Должность:* {row.get('title', '---')}
💼 *Компания:* {row.get('company', '---')}
💰 *ЗП:* {row.get('salary_range') or row.get('salary') or '---'}

[Подробнее на HH]({row['link']})"""

async def main():
    csv_path = get_today_processed_csv()
    df = pd.read_csv(csv_path)

    # Приводим published_date_dt в datetime
    df["published_date_dt"] = pd.to_datetime(df["published_date_dt"], errors="coerce")

    # Фильтрация по сегодняшнему дню
    today = pd.Timestamp.today().normalize()
    df_today = df[df["published_date_dt"].dt.normalize() == today]

    if df_today.empty:
        print("Сегодня нет новых вакансий для отправки.")
        return

    bot = Bot(token=BOT_TOKEN)
    for _, row in df_today.iterrows():
        text = format_message(row)
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=text, parse_mode="Markdown")

    print(f"Отправлено {len(df_today)} вакансий за сегодня.")

def run_publisher():
    asyncio.run(main())

if __name__ == "__main__":
    run_publisher()
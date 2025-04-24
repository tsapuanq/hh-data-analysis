import pandas as pd
import asyncio
import os
import random
from datetime import datetime
from telegram import Bot
from src.config import BOT_TOKEN, CHANNEL_USERNAME, get_today_processed_csv
from src.llm_summary import summarize_description_llm, filter_vacancy_llm

# ——— Путь до файла отправленных ссылок ———
SENT_LINKS_PATH = "data/sent_links.txt"

# ——— Форматирование вакансии для Telegram ———
def format_message(row: pd.Series, summary: dict) -> str:
    return f"""
🌐 *Город:* {row.get('location', '---')}
📅 *Должность:* {row.get('title', '---')}
💼 *Компания:* {row.get('company', '---')}
💰 *ЗП:* {row.get('salary_range') or '---'}

🎓 *Опыт:* {row.get('experience', '---')}
📂 *Тип занятости:* {row.get('employment_type', '---')}
📆 *График:* {row.get('schedule', '---')}
🕒 *Рабочие часы:* {row.get('working_hours', '---')}
🏠 *Формат работы:* {row.get('work_format', '---')}
📅 *Дата публикации:* {row.get('published_date', '---')}

💾 *Обязанности:*
{summary.get('responsibilities', 'Не указано')}

🌟 *Требования:*
{summary.get('requirements', 'Не указано')}

🏢 *О компании:*
{summary.get('about_company', 'Не указано')}

🔎 [Подробнее на HH]({row['link']})
""".strip()

# ——— Загрузка ранее отправленных ссылок ———
def load_sent_links(path: str = SENT_LINKS_PATH) -> set:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

# ——— Добавление новых отправленных ссылок ———
def append_sent_links(links: list, path: str = SENT_LINKS_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for link in links:
            f.write(link + "\n")

# ——— Загрузка CSV и фильтрация по дате ———
def load_today_rows() -> pd.DataFrame:
    csv_path = get_today_processed_csv()
    if not os.path.exists(csv_path):
        print(f"❌ CSV не найден: {csv_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
        today_str = datetime.now().strftime("%Y-%m-%d")
        df = df[df["published_date_dt"] == "2025-04-23"]
        return df
    except Exception as e:
        print(f"❌ Ошибка чтения CSV: {e}")
        return pd.DataFrame()

# ——— Основной пайплайн публикации вакансий ———
async def main():
    df = load_today_rows()
    if df.empty:
        print("ℹ️ Сегодня нет новых вакансий.")
        return

    sent_links = load_sent_links()
    df = df[~df["link"].isin(sent_links)].copy()

    if df.empty:
        print("ℹ️ Все вакансии уже были отправлены ранее.")
        return

    filtered = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        is_relevant = filter_vacancy_llm(row["title"], row["description"])
        print(f"[Gemini Filter] {row['title']} → {'✅' if is_relevant else '❌'}")

        if is_relevant:
            filtered.append(row)

        await asyncio.sleep(4.5)  # задержка из-за лимита Gemini API

    if not filtered:
        print("❌ Нет релевантных вакансий после фильтрации.")
        return

    df_filtered = pd.DataFrame(filtered)
    bot = Bot(token=BOT_TOKEN)

    for i, (_, row) in enumerate(df_filtered.iterrows(), 1):
        summary = summarize_description_llm(row["description"])
        text = format_message(row, summary)
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=text, parse_mode="Markdown")
        print(f"✅ [{i}/{len(df_filtered)}] Вакансия отправлена.")

        if i < len(df_filtered):
            delay = random.uniform(3, 10)
            print(f"⏱️ Задержка перед следующей: {delay:.2f} сек.")
            await asyncio.sleep(delay)

    # ——— Сохраняем отправленные ссылки ———
    append_sent_links(df_filtered["link"].tolist())
    print(f"\n📬 Всего отправлено: {len(df_filtered)} вакансий.")

def run_publisher():
    return main()
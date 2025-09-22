from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from datetime import datetime, timedelta, time

# ====== Настройки ======
TOKEN = "7997003832:AAFW8urdKFz5BRElfOG7A9q-YNwG3nFPOFw"
GSHEET_JSON = "bot-project-json.json"
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1atJgfYuwtXBP1uF0uHlRXp611R8mOKwndPQxi9MzUqE/edit?gid=0"
CHAT_ID = 617969116  

# ====== Подключение к Google Sheets ======
gc = gspread.service_account(filename=GSHEET_JSON)
sheet = gc.open_by_url(GSHEET_URL)
worksheet = sheet.sheet1


# ====== Вспомогательные функции ======
def get_records():
    return worksheet.get_all_records()


def get_next_lesson():
    now = datetime.now()
    for lesson in get_records():
        try:
            lesson_date = datetime.strptime(lesson['lesson_date'], "%d.%m.%Y %H:%M")
            if lesson_date >= now:
                return {
                    'title': lesson['lesson_title'],
                    'date': lesson['lesson_date'],
                    'homework_link': lesson.get('homework_for_the_next_lesson', "").replace('"', '').strip(),
                    'meeting': lesson.get('meeting_link', "").replace('"', '').strip(),
                    'summary': lesson.get('lesson_summary', "").strip(),
                    'hour': lesson_date.hour,
                    'minute': lesson_date.minute,
                    'datetime': lesson_date
                }
        except Exception as e:
            print("Ошибка при обработке урока:", e)
            continue
    return None


def get_last_lesson():
    now = datetime.now()
    past_lessons = []
    for lesson in get_records():
        try:
            lesson_date = datetime.strptime(lesson['lesson_date'], "%d.%m.%Y %H:%M")
            if lesson_date <= now:
                past_lessons.append({
                    'title': lesson['lesson_title'],
                    'date': lesson['lesson_date'],
                    'homework_link': lesson.get('homework_for_the_next_lesson', "").replace('"', '').strip(),
                    'meeting': lesson.get('meeting_link', "").replace('"', '').strip(),
                    'summary': lesson.get('lesson_summary', "").strip()
                })
        except Exception as e:
            print("Ошибка при обработке урока:", e)
            continue
    if past_lessons:
        return past_lessons[-1]
    return None


# ====== Команды бота ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    START_TEXT = """
Привет! 👋 Я — твой бот-наставник по учебе!  

📅 /lessons — ближайший урок  
📝 /homework — домашка  
📖 /summary — саммари последнего урока  
🔗 /meeting — ссылка на встречу  
📤 /submit — отправка домашки
    """
    await update.message.reply_text(START_TEXT)


async def lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = get_next_lesson()
    if lesson:
        buttons = []
        if lesson['homework_link']:
            buttons.append([InlineKeyboardButton("📘 Домашка", url=lesson['homework_link'])])
        if lesson['meeting']:
            buttons.append([InlineKeyboardButton("🔗 Встреча", url=lesson['meeting'])])

        text = f"Ближайший урок:\n📖 {lesson['title']}\n🗓 {lesson['date']}"
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text("Ближайший урок пока не найден.")


async def homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = get_next_lesson()
    if lesson and lesson['homework_link']:
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Открыть домашку", url=lesson['homework_link'])]])
        await update.message.reply_text("Домашнее задание к следующему уроку:", reply_markup=button)
    else:
        await update.message.reply_text("Домашнее задание пока не назначено.")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_lesson = get_last_lesson()
    if last_lesson and last_lesson['summary']:
        text = f"Саммари последнего урока ({last_lesson['title']}):\n{last_lesson['summary']}"
    else:
        text = "Саммари пока недоступно."
    await update.message.reply_text(text)


async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришли файл или текст с твоим домашним заданием сюда.")


async def meeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = get_next_lesson()
    if lesson and lesson['meeting']:
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к встрече", url=lesson['meeting'])]])
        await update.message.reply_text("Ссылка на ближайший урок:", reply_markup=button)
    else:
        await update.message.reply_text("Ссылка на урок пока не назначена.")


# ====== Приёмка домашки (файлы и текст) ======
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        await update.message.document.download_to_drive()
        await update.message.reply_text("✅ Файл домашки сохранён.")
    elif update.message.text:
        await update.message.reply_text(f"✅ Принял текст домашки:\n{update.message.text}")


# ====== Напоминания ======
async def lesson_reminder_job(context):
    lesson = get_next_lesson()
    if lesson:
        await context.bot.send_message(chat_id=CHAT_ID,
                                       text=f"📌 Напоминание: урок '{lesson['title']}' будет {lesson['date']}")


async def homework_reminder_job(context):
    lesson = get_next_lesson()
    if lesson and lesson['homework_link']:
        await context.bot.send_message(chat_id=CHAT_ID,
                                       text=f"📝 Напоминание: сделай домашку — {lesson['homework_link']}")


async def hourly_check_job(context):
    """Каждые 30 минут проверяет, нет ли урока через час."""
    lesson = get_next_lesson()
    if lesson:
        now = datetime.now()
        if timedelta(minutes=50) <= (lesson['datetime'] - now) <= timedelta(minutes=70):
            await context.bot.send_message(chat_id=CHAT_ID,
                                           text=f"⏰ Через час урок '{lesson['title']}' ({lesson['date']})")


# ====== Запуск бота ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lessons", lessons))
    app.add_handler(CommandHandler("homework", homework))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("meeting", meeting))
    app.add_handler(CommandHandler("submit", submit))

    # Приёмка домашки
    app.add_handler(MessageHandler(filters.Document.ALL | filters.TEXT, handle_homework))

    # ====== Job Queue ======
    jq = app.job_queue

    # Напоминания про уроки (среда=2, пятница=4 в 10:00)
    jq.run_daily(lesson_reminder_job, time=time(10, 0), days=(2, 4))

    # Напоминания про домашку (вторник=1, четверг=3, пятница=4 в 10:00)
    jq.run_daily(homework_reminder_job, time=time(10, 0), days=(1, 3, 4))

    # Проверка "урок через час" каждые 30 минут
    jq.run_repeating(hourly_check_job, interval=1800, first=10)

    print("Бот запущен...")
    app.run_polling()


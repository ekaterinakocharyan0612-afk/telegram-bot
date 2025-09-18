from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from datetime import datetime, timedelta, time

# ====== Настройки ======
TOKEN = "7997003832:AAFW8urdKFz5BRElfOG7A9q-YNwG3nFPOFw"
GSHEET_JSON = "bot-project-json.json"
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1atJgfYuwtXBP1uF0uHlRXp611R8mOKwndPQxi9MzUqE/edit?gid=0"
CHAT_ID = 617969116  # Твой chat_id

# ====== Подключение к Google Sheets ======
gc = gspread.service_account(filename=GSHEET_JSON)
sheet = gc.open_by_url(GSHEET_URL)
worksheet = sheet.sheet1
records = worksheet.get_all_records()

# ====== Вспомогательные функции ======
def get_next_lesson():
    now = datetime.now()
    for lesson in records:
        try:
            lesson_date = datetime.strptime(lesson['lesson_date'], "%d.%m.%Y %H:%M")
            if lesson_date >= now:
                return {
                    'title': lesson['lesson_title'],
                    'date': lesson['lesson_date'],
                    'homework_link': lesson.get('homework_for_the_next_lesson', "").replace('"','').strip(),
                    'meeting': lesson.get('meeting_link', "").replace('"','').strip(),
                    'summary': lesson.get('lesson_summary', "").strip(),
                    'hour': lesson_date.hour,
                    'minute': lesson_date.minute
                }
        except:
            continue
    return None

def get_last_lesson():
    now = datetime.now()
    past_lessons = []
    for lesson in records:
        try:
            lesson_date = datetime.strptime(lesson['lesson_date'], "%d.%m.%Y %H:%M")
            if lesson_date <= now:
                past_lessons.append({
                    'title': lesson['lesson_title'],
                    'date': lesson['lesson_date'],
                    'homework_link': lesson.get('homework_for_the_next_lesson', "").replace('"','').strip(),
                    'meeting': lesson.get('meeting_link', "").replace('"','').strip(),
                    'summary': lesson.get('lesson_summary', "").strip()
                })
        except:
            continue
    if past_lessons:
        return past_lessons[-1]
    return None

# ====== Команды бота ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    START_TEXT = """
Привет! 👋 Я — твой бот-наставник по учебе!  

С моим ботом ты сможешь:  
📅 Узнавать расписание уроков  
📝 Проверять домашку  
📖 Читать саммари уроков  
🔗 Быстро подключаться к онлайн-занятиям  
📤 Отправлять свои задания через чат  

Команды:  
/lessons — ближайший урок  
/homework — домашка  
/summary — саммари последнего урока  
/meeting — ссылка на встречу  
/submit — отправка домашки
    """
    await update.message.reply_text(START_TEXT)

async def lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = get_next_lesson()
    if lesson:
        text = f"Ближайший урок:\n{lesson['title']}\nДата: {lesson['date']}"
        if lesson['homework_link']:
            text += f"\nДомашка: {lesson['homework_link']}"
        if lesson['meeting']:
            text += f"\nСсылка на встречу: {lesson['meeting']}"
    else:
        text = "Ближайший урок пока не найден."
    await update.message.reply_text(text)

async def homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = get_next_lesson()
    if lesson and lesson['homework_link']:
        text = f"Домашнее задание к следующему уроку:\n{lesson['homework_link']}"
    else:
        text = "Домашнее задание пока не назначено."
    await update.message.reply_text(text)

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_lesson = get_last_lesson()
    if last_lesson and last_lesson['summary']:
        text = f"Саммари последнего урока ({last_lesson['title']}):\n{last_lesson['summary']}"
    else:
        text = "Саммари пока недоступно."
    await update.message.reply_text(text)

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пришли файл или текст с твоим домашним заданием через чат.")

async def meeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = get_next_lesson()
    if lesson and lesson['meeting']:
        await update.message.reply_text(f"Ссылка на ближайший урок:\n{lesson['meeting']}")
    else:
        await update.message.reply_text("Ссылка на урок пока не назначена.")

# ====== Функции напоминаний через job_queue ======
async def lesson_reminder_job(context):
    lesson = get_next_lesson()
    if lesson:
        await context.bot.send_message(chat_id=CHAT_ID, text=f"📌 Напоминание: урок '{lesson['title']}' будет {lesson['date']}")

async def homework_reminder_job(context):
    lesson = get_next_lesson()
    if lesson and lesson['homework_link']:
        await context.bot.send_message(chat_id=CHAT_ID, text=f"📝 Не забудь сделать домашку: {lesson['homework_link']}")

async def check_homework_job(context):
    await context.bot.send_message(chat_id=CHAT_ID, text="✅ Сделал ли ты домашнее задание к следующему уроку?")

# ====== Запуск бота ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Регистрация команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lessons", lessons))
    app.add_handler(CommandHandler("homework", homework))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("meeting", meeting))
    app.add_handler(CommandHandler("submit", submit))

    # ====== Job Queue для напоминаний ======
    jq = app.job_queue

    # Урок: пятница, суббота в 10:00
    jq.run_daily(lesson_reminder_job, time=time(10,0), days=(4,5))  # 0=Mon,4=Fri,5=Sat

    # Урок: воскресенье за 1 час до начала
    next_lesson = get_next_lesson()
    if next_lesson:
        lesson_time = datetime.strptime(next_lesson['date'], "%d.%m.%Y %H:%M")
        lesson_time -= timedelta(hours=1)
        jq.run_daily(lesson_reminder_job, time=lesson_time.time(), days=(6,))  # Sun=6

    # Домашка: среда, пятница
    jq.run_daily(homework_reminder_job, time=time(10,0), days=(2,4))  # Wed=2,Fri=4

    # Проверка домашки: суббота
    jq.run_daily(check_homework_job, time=time(18,0), days=(5,))  # Sat=5

    print("Бот запущен...")
    app.run_polling()


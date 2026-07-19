import os
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello Arham! I am your Autonomous Agent.\n\n"
        "Send me any task and I will get it done.\n\n"
        "Examples:\n"
        "- find python jobs on internshala\n"
        "- search for AI internships and apply to 2\n"
        "- save a report of today's applications"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text("Got it! Working on it now...")
    try:
        process = subprocess.Popen(
            ["python3", "agent.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=user_message, timeout=300)
        if stdout:
            lines = stdout.strip().split("\n")
            final_answer = ""
            for line in lines:
                if "FINAL ANSWER:" in line:
                    final_answer = stdout.split("FINAL ANSWER:")[-1].strip()
                    break
            if final_answer:
                await update.message.reply_text(final_answer[:4000])
            else:
                await update.message.reply_text("Task completed!")
        else:
            await update.message.reply_text("Task completed!")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("Task is taking too long — check your email for the report.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Telegram bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
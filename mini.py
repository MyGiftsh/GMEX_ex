# mini.py
import os
import logging
import json
from typing import Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# --- Конфигурация ---
# Лучше хранить токен в env var: export GMEX_TOKEN="..."
TOKEN = os.environ.get("GMEX_TOKEN") or "8584230387:AAF1FuIldR1LBHcmRAUHbi7zVtsgCxuJKZc"  # <- Если вы предоставили токен, он здесь
# Замените на эту строку в mini.py. Используем v=7 для 100% сброса кэша.
WEB_APP_URL = os.environ.get("GMEX_WEBAPP_URL") or "https://mygiftsh.github.io/GMEX_ex/?v=7"  # обязательно HTTPS
ADMIN = os.environ.get("GMEX_ADMIN") or "@gadzhigg"  # может быть "@username" или строка с числовым id

BOT_NAME = "gmex"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- ХЭЛПЕРЫ ---
def format_admin_message(data: dict, user_info: dict) -> str:
    # data — словарь из WebApp
    lines = [
        "🚨 НОВАЯ ЗАЯВКА — gmex 🚨",
        f"Тип: {data.get('type', 'N/A')}",
        f"Сумма: {data.get('amount', 'N/A')} ₽",
        f"Кошелек/Сеть: {data.get('wallet', 'N/A')}",
        f"ФИО: {data.get('fio', 'N/A')}",
        f"TG id: {user_info.get('id')}",
        f"TG ник: @{user_info.get('username')}" if user_info.get('username') else f"TG ник: N/A",
        f"Время: {data.get('timestamp', 'N/A')}"
    ]
    return "\n".join(lines)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет стартовое сообщение с кнопкой WebApp."""
    keyboard = [
        [InlineKeyboardButton(text="Открыть gmex", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    await update.message.reply_text(
        text=f"Привет! Это {BOT_NAME}. Нажми кнопку, чтобы открыть обменник.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def web_app_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает WEB_APP_DATA (в telegram это приходит как message.web_app_data)."""
    # В python-telegram-bot данные web app приходят как update.message.web_app_data.data (строка)
    message = update.effective_message
    user = update.effective_user or {}
    try:
        raw = message.web_app_data.data if message and message.web_app_data else None
        if not raw:
            await message.reply_text("Пустые данные от WebApp.")
            return
        data = json.loads(raw)
    except Exception as e:
        logger.exception("Ошибка парсинга web_app_data")
        await message.reply_text("Ошибка при обработке данных заявки.")
        return

    # Валидация минимальных полей
    amount = data.get("amount")
    wallet = data.get("wallet")
    fio = data.get("fio")
    if not amount or not wallet or not fio:
        await message.reply_text("Неверные данные заявки — проверьте форму.")
        return

    # Сообщение админу
    admin_text = format_admin_message(data, {"id": user.id, "username": user.username})
    try:
        # отправляем админу (ADMIN может быть username или id)
        if isinstance(ADMIN, str) and ADMIN.startswith("@"):
            await context.bot.send_message(chat_id=ADMIN, text=admin_text)
        else:
            # попробуем привести к int
            try:
                chat_id = int(ADMIN)
            except Exception:
                chat_id = ADMIN
            await context.bot.send_message(chat_id=chat_id, text=admin_text)
    except Exception as e:
        logger.exception("Не удалось отправить сообщение админу")
        # сообщаем клиенту что заявка принята, но админ уведомление не доставлено
        await message.reply_text("Заявка получена, но не удалось уведомить администратора.")
        return

    # подтверждение пользователю
    await message.reply_text("Ваша заявка принята — оператор свяжется с вами в ближайшее время. Спасибо!")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Команда не распознана. Используйте /start.")

# --- Основной запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    app. add_handler(CommandHandler("start", start))
    # handler для web_app_data (фильтр)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("Запуск бота gmex...")
    app.run_polling()

if __name__ == "__main__":
    main()

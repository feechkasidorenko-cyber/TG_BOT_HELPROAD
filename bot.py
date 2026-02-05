import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from telegram.error import TelegramError
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
PORT = int(os.environ.get('PORT', 8443))

# Состояния для ConversationHandler
LOCATION, PHONE, CAR_DETAILS, ACCIDENT_DETAILS, PHOTOS = range(5)

# Клавиатуры
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 Отправить номер", request_contact=True)],
        [KeyboardButton("📍 Отправить местоположение", request_location=True)],
        ["🚗 Данные автомобиля"],
        ["📝 Описание ДТП"],
        ["📷 Прикрепить фото"],
        ["✅ Отправить заявку"]
    ], resize_keyboard=True)

# Хранилище данных заявки
user_data_store = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Я бот для оформления заявки вызова аварийного комиссара.\n"
        "Пожалуйста, последовательно заполните данные:\n\n"
        "1. 📱 Предоставьте номер телефона\n"
        "2. 📍 Укажите место ДТП\n"
        "3. 🚗 Введите данные автомобиля\n"
        "4. 📝 Опишите обстоятельства ДТП\n"
        "5. 📷 Прикрепите фотографии\n"
        "6. ✅ Отправьте заявку\n\n"
        "После отправки с вами свяжутся в течение 15 минут."
    )
    
    user_data_store[user.id] = {
        'user_id': user.id,
        'username': user.username,
        'full_name': f"{user.first_name} {user.last_name or ''}".strip(),
        'phone': None,
        'location': None,
        'car_details': None,
        'accident_details': None,
        'photos': [],
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'new'
    }
    
    await update.message.reply_text(welcome_text, reply_markup=main_keyboard())
    return LOCATION

# Обработка местоположения
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    location = update.message.location
    
    if user.id in user_data_store:
        user_data_store[user.id]['location'] = {
            'latitude': location.latitude,
            'longitude': location.longitude
        }
    
    await update.message.reply_text(
        "📍 Местоположение получено! Теперь отправьте номер телефона.",
        reply_markup=main_keyboard()
    )
    return PHONE

# Обработка контакта
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact
    
    if user.id in user_data_store:
        user_data_store[user.id]['phone'] = contact.phone_number
    
    await update.message.reply_text(
        "📱 Номер телефона получен! Теперь введите данные автомобиля:\n"
        "• Марка и модель\n"
        "• Госномер\n"
        "• VIN (при наличии)",
        reply_markup=main_keyboard()
    )
    return CAR_DETAILS

# Обработка данных автомобиля
async def handle_car_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    if user.id in user_data_store:
        user_data_store[user.id]['car_details'] = text
    
    await update.message.reply_text(
        "🚗 Данные автомобиля сохранены! Теперь опишите обстоятельства ДТП:\n"
        "• Дата и время ДТП\n"
        "• Обстоятельства происшествия\n"
        "• Есть ли пострадавшие\n"
        "• Количество участников",
        reply_markup=main_keyboard()
    )
    return ACCIDENT_DETAILS

# Обработка описания ДТП
async def handle_accident_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    if user.id in user_data_store:
        user_data_store[user.id]['accident_details'] = text
    
    await update.message.reply_text(
        "📝 Описание ДТП сохранено! Теперь прикрепите фотографии (до 5 фото).\n"
        "Отправьте фотографии или нажмите '✅ Отправить заявку' для завершения.",
        reply_markup=main_keyboard()
    )
    return PHOTOS

# Обработка фотографий
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        return PHOTOS
    
    if update.message.photo:
        photo = update.message.photo[-1]
        user_data_store[user.id]['photos'].append(photo.file_id)
        
        photo_count = len(user_data_store[user.id]['photos'])
        
        if photo_count < 5:
            await update.message.reply_text(
                f"📷 Фотография #{photo_count} получена. "
                f"Можно отправить еще {5-photo_count}.",
                reply_markup=main_keyboard()
            )
        else:
            await update.message.reply_text(
                "✅ Максимальное количество фотографий достигнуто. "
                "Нажмите '✅ Отправить заявку' для завершения.",
                reply_markup=main_keyboard()
            )
    
    return PHOTOS

# Отправка заявки
async def send_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "⚠️ Заявка не найдена. Начните заново с /start",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END
    
    data = user_data_store[user.id]
    
    # Проверяем обязательные поля
    if not all([data.get('phone'), data.get('location'), data.get('car_details'), data.get('accident_details')]):
        missing_fields = []
        if not data.get('phone'): missing_fields.append("номер телефона")
        if not data.get('location'): missing_fields.append("местоположение")
        if not data.get('car_details'): missing_fields.append("данные автомобиля")
        if not data.get('accident_details'): missing_fields.append("описание ДТП")
        
        await update.message.reply_text(
            f"⚠️ Заполните все обязательные поля: {', '.join(missing_fields)}",
            reply_markup=main_keyboard()
        )
        return PHOTOS
    
    try:
        # Формируем сообщение для администратора
        admin_message = (
            "🚨 НОВАЯ ЗАЯВКА АВАРИЙНОГО КОМИССАРА\n\n"
            f"👤 Клиент: {data['full_name']}\n"
            f"📱 Телефон: {data['phone']}\n"
            f"📍 Местоположение: https://maps.google.com/?q={data['location']['latitude']},{data['location']['longitude']}\n"
            f"🚗 Автомобиль: {data['car_details']}\n"
            f"📝 Описание ДТП:\n{data['accident_details']}\n"
            f"📷 Фотографий: {len(data['photos'])}\n"
            f"🕒 Время заявки: {data['created_at']}\n"
            f"🆔 ID пользователя: {user.id}"
        )
        
        # Отправляем администратору
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_message
            )
            
            # Отправляем фотографии
            if data['photos']:
                for photo_id in data['photos'][:5]:
                    try:
                        await context.bot.send_photo(
                            chat_id=ADMIN_CHAT_ID,
                            photo=photo_id
                        )
                    except Exception as e:
                        logger.error(f"Ошибка отправки фото: {e}")
        
        # Подтверждение пользователю
        await update.message.reply_text(
            "✅ Заявка успешно отправлена!\n\n"
            f"📞 С вами свяжутся в течение 15 минут.\n"
            f"Ожидайте звонка по номеру: {data['phone']}\n\n"
            "Для новой заявки нажмите /start",
            reply_markup=ReplyKeyboardMarkup([['/start']], resize_keyboard=True)
        )
        
        # Очищаем данные
        if user.id in user_data_store:
            del user_data_store[user.id]
            
    except Exception as e:
        logger.error(f"Ошибка отправки заявки: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при отправке заявки. Попробуйте еще раз.",
            reply_markup=main_keyboard()
        )
        return PHOTOS
    
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in user_data_store:
        del user_data_store[user.id]
    
    await update.message.reply_text(
        "Заявка отменена. Для новой заявки нажмите /start",
        reply_markup=ReplyKeyboardMarkup([['/start']], resize_keyboard=True)
    )
    return ConversationHandler.END

# Обработка текста (кнопки меню)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "✅ Отправить заявку":
        return await send_application(update, context)
    elif text in ["🚗 Данные автомобиля", "📝 Описание ДТП", "📷 Прикрепить фото"]:
        # Просто игнорируем повторные нажатия на эти кнопки
        return await context.application.persistence.get_user_context(update.effective_user.id)
    else:
        # Если пользователь пишет текст вне состояний
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки меню или начните с /start",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END

# Основная функция
async def main():
    # Проверяем наличие токена
    if not TOKEN:
        logger.error("Токен бота не найден! Установите переменную окружения TELEGRAM_BOT_TOKEN")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Настраиваем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & filters.Regex('^📍'), lambda u, c: u.message.reply_text("Пожалуйста, нажмите кнопку '📍 Отправить местоположение'", reply_markup=main_keyboard()))
            ],
            PHONE: [
                MessageHandler(filters.CONTACT, handle_contact),
                MessageHandler(filters.TEXT & filters.Regex('^📱'), lambda u, c: u.message.reply_text("Пожалуйста, нажмите кнопку '📱 Отправить номер'", reply_markup=main_keyboard()))
            ],
            CAR_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_car_details)
            ],
            ACCIDENT_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accident_details)
            ],
            PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photos),
                MessageHandler(filters.TEXT & filters.Regex('^✅'), send_application)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & filters.Regex('^✅'), send_application)
        ]
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Запускаем бота с вебхуком на Render
    webhook_url = f"https://telegram-commissioner-bot.onrender.com/{TOKEN}"
    logger.info(f"Запуск бота с вебхуком: {webhook_url}")
    
    await application.initialize()
    await application.start()
    
    # Устанавливаем вебхук
    await application.bot.set_webhook(url=webhook_url)
    
    # Запускаем сервер
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=webhook_url
    )
    
    logger.info("Бот запущен и готов к работе!")
    
    # Бесконечный цикл
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка бота...")
    finally:
        await application.stop()

if __name__ == '__main__':
    asyncio.run(main())

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

# Состояния для ConversationHandler
LOCATION, PHONE, CAR_DETAILS, ACCIDENT_DETAILS, PHOTOS = range(5)

# Хранилище данных заявки
user_data_store = {}

# Клавиатуры
def get_contact_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 Отправить номер", request_contact=True)]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_location_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 Отправить местоположение", request_location=True)]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_car_keyboard():
    return ReplyKeyboardMarkup([
        ["🚗 Уже заполнил данные"]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_accident_keyboard():
    return ReplyKeyboardMarkup([
        ["📝 Уже заполнил описание"]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_photos_keyboard():
    return ReplyKeyboardMarkup([
        ["✅ Отправить заявку без фото"],
        ["📷 Прикрепить фото"]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_final_keyboard():
    return ReplyKeyboardMarkup([
        ["✅ Отправить заявку"]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_start_keyboard():
    return ReplyKeyboardMarkup([
        ["🚀 Начать оформление заявки"]
    ], resize_keyboard=True, one_time_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Я бот для оформления заявки вызова аварийного комиссара.\n"
        "Пожалуйста, заполните данные для вызова комиссара.\n\n"
        "После отправки заявки с вами свяжутся в течение 15 минут."
    )
    
    # Инициализируем данные пользователя
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
    
    await update.message.reply_text(welcome_text, reply_markup=get_start_keyboard())
    
    # Просим отправить номер телефона
    await update.message.reply_text(
        "📱 **Шаг 1 из 5: Номер телефона**\n\n"
        "Пожалуйста, нажмите кнопку ниже, чтобы отправить номер телефона для связи:",
        reply_markup=get_contact_keyboard(),
        parse_mode='Markdown'
    )
    
    return PHONE

# Обработка контакта (телефон)
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "Пожалуйста, начните с /start",
            reply_markup=get_start_keyboard()
        )
        return ConversationHandler.END
    
    contact = update.message.contact
    user_data_store[user.id]['phone'] = contact.phone_number
    
    await update.message.reply_text(
        f"✅ **Номер телефона получен:** `{contact.phone_number}`\n\n"
        "📍 **Шаг 2 из 5: Местоположение ДТП**\n\n"
        "Пожалуйста, отправьте геолокацию места ДТП:",
        reply_markup=get_location_keyboard(),
        parse_mode='Markdown'
    )
    
    return LOCATION

# Обработка местоположения
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "Пожалуйста, начните с /start",
            reply_markup=get_start_keyboard()
        )
        return ConversationHandler.END
    
    location = update.message.location
    user_data_store[user.id]['location'] = {
        'latitude': location.latitude,
        'longitude': location.longitude
    }
    
    await update.message.reply_text(
        f"✅ **Местоположение получено!**\n\n"
        "🚗 **Шаг 3 из 5: Данные автомобиля**\n\n"
        "Пожалуйста, введите данные автомобиля:\n"
        "• Марка и модель\n"
        "• Госномер\n"
        "• VIN (при наличии)\n\n"
        "Пример: *Toyota Camry, А123ВС77, JTNBB46KX00345678*\n\n"
        "Введите данные в одном сообщении:",
        reply_markup=get_car_keyboard(),
        parse_mode='Markdown'
    )
    
    return CAR_DETAILS

# Обработка данных автомобиля
async def handle_car_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "Пожалуйста, начните с /start",
            reply_markup=get_start_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text.strip()
    
    # Если пользователь нажал кнопку "🚗 Уже заполнил данные"
    if text == "🚗 Уже заполнил данные":
        # Проверяем, были ли уже введены данные
        if user_data_store[user.id].get('car_details'):
            await update.message.reply_text(
                "📝 **Шаг 4 из 5: Описание ДТП**\n\n"
                "Пожалуйста, опишите обстоятельства ДТП:\n"
                "• Дата и время ДТП\n"
                "• Обстоятельства происшествия\n"
                "• Есть ли пострадавшие\n"
                "• Количество участников\n\n"
                "Введите описание в одном сообщении:",
                reply_markup=get_accident_keyboard(),
                parse_mode='Markdown'
            )
            return ACCIDENT_DETAILS
        else:
            await update.message.reply_text(
                "Вы еще не ввели данные автомобиля. Пожалуйста, введите данные:",
                reply_markup=get_car_keyboard()
            )
            return CAR_DETAILS
    
    # Сохраняем данные автомобиля
    user_data_store[user.id]['car_details'] = text
    
    await update.message.reply_text(
        f"✅ **Данные автомобиля сохранены!**\n\n"
        "📝 **Шаг 4 из 5: Описание ДТП**\n\n"
        "Пожалуйста, опишите обстоятельства ДТП:\n"
        "• Дата и время ДТП\n"
        "• Обстоятельства происшествия\n"
        "• Есть ли пострадавшие\n"
        "• Количество участников\n\n"
        "Введите описание в одном сообщении:",
        reply_markup=get_accident_keyboard(),
        parse_mode='Markdown'
    )
    
    return ACCIDENT_DETAILS

# Обработка описания ДТП
async def handle_accident_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "Пожалуйста, начните с /start",
            reply_markup=get_start_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text.strip()
    
    # Если пользователь нажал кнопку "📝 Уже заполнил описание"
    if text == "📝 Уже заполнил описание":
        # Проверяем, было ли уже введено описание
        if user_data_store[user.id].get('accident_details'):
            await update.message.reply_text(
                "📷 **Шаг 5 из 5: Фотографии**\n\n"
                "Вы можете прикрепить фотографии ДТП (до 5 фото):\n"
                "• Фото места происшествия\n"
                "• Фото повреждений\n"
                "• Фото документов\n\n"
                "Отправляйте фотографии по одной или нажмите кнопку ниже:",
                reply_markup=get_photos_keyboard()
            )
            return PHOTOS
        else:
            await update.message.reply_text(
                "Вы еще не ввели описание ДТП. Пожалуйста, опишите обстоятельства:",
                reply_markup=get_accident_keyboard()
            )
            return ACCIDENT_DETAILS
    
    # Сохраняем описание ДТП
    user_data_store[user.id]['accident_details'] = text
    
    await update.message.reply_text(
        f"✅ **Описание ДТП сохранено!**\n\n"
        "📷 **Шаг 5 из 5: Фотографии**\n\n"
        "Вы можете прикрепить фотографии ДТП (до 5 фото):\n"
        "• Фото места происшествия\n"
        "• Фото повреждений\n"
        "• Фото документов\n\n"
        "Отправляйте фотографии по одной или нажмите кнопку ниже:",
        reply_markup=get_photos_keyboard()
    )
    
    return PHOTOS

# Обработка фотографий
async def handle_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "Пожалуйста, начните с /start",
            reply_markup=get_start_keyboard()
        )
        return ConversationHandler.END
    
    text = update.message.text if update.message.text else ""
    
    # Если пользователь хочет отправить заявку без фото
    if text == "✅ Отправить заявку без фото":
        return await send_application(update, context)
    
    # Если пользователь хочет прикрепить фото
    if text == "📷 Прикрепить фото":
        await update.message.reply_text(
            "Пожалуйста, отправьте фотографии. Можно отправить до 5 фото.\n"
            "После отправки фото нажмите '✅ Отправить заявку'",
            reply_markup=get_final_keyboard()
        )
        return PHOTOS
    
    # Если это фото
    if update.message.photo:
        photo = update.message.photo[-1]
        user_data_store[user.id]['photos'].append(photo.file_id)
        
        photo_count = len(user_data_store[user.id]['photos'])
        
        if photo_count < 5:
            await update.message.reply_text(
                f"✅ Фото #{photo_count} получено.\n"
                f"Можно отправить еще {5 - photo_count} фото.\n\n"
                "Продолжайте отправлять фото или нажмите '✅ Отправить заявку'",
                reply_markup=get_final_keyboard()
            )
        else:
            await update.message.reply_text(
                "✅ Максимальное количество фото (5) достигнуто.\n"
                "Нажмите '✅ Отправить заявку' для завершения",
                reply_markup=get_final_keyboard()
            )
    
    return PHOTOS

# Отправка заявки
async def send_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "Пожалуйста, начните с /start",
            reply_markup=get_start_keyboard()
        )
        return ConversationHandler.END
    
    data = user_data_store[user.id]
    
    # Проверяем заполнены ли все обязательные поля
    missing_fields = []
    if not data.get('phone'): 
        missing_fields.append("номер телефона")
    if not data.get('location'): 
        missing_fields.append("местоположение")
    if not data.get('car_details'): 
        missing_fields.append("данные автомобиля")
    if not data.get('accident_details'): 
        missing_fields.append("описание ДТП")
    
    if missing_fields:
        error_text = "⚠️ **Не все данные заполнены!**\n\n"
        
        if not data.get('phone'):
            error_text += "📱 **Номер телефона:** не указан\n"
            await update.message.reply_text(
                error_text + "\nПожалуйста, отправьте номер телефона:",
                reply_markup=get_contact_keyboard(),
                parse_mode='Markdown'
            )
            return PHONE
        elif not data.get('location'):
            error_text += "📍 **Местоположение:** не указано\n"
            await update.message.reply_text(
                error_text + "\nПожалуйста, отправьте местоположение:",
                reply_markup=get_location_keyboard(),
                parse_mode='Markdown'
            )
            return LOCATION
        elif not data.get('car_details'):
            error_text += "🚗 **Данные автомобиля:** не указаны\n"
            await update.message.reply_text(
                error_text + "\nПожалуйста, введите данные автомобиля:",
                reply_markup=get_car_keyboard(),
                parse_mode='Markdown'
            )
            return CAR_DETAILS
        elif not data.get('accident_details'):
            error_text += "📝 **Описание ДТП:** не указано\n"
            await update.message.reply_text(
                error_text + "\nПожалуйста, опишите обстоятельства ДТП:",
                reply_markup=get_accident_keyboard(),
                parse_mode='Markdown'
            )
            return ACCIDENT_DETAILS
    
    try:
        # Формируем сообщение для администратора
        map_url = f"https://www.google.com/maps?q={data['location']['latitude']},{data['location']['longitude']}"
        
        admin_message = (
            "🚨 *НОВАЯ ЗАЯВКА АВАРИЙНОГО КОМИССАРА*\n\n"
            f"👤 *Клиент:* {data['full_name']}\n"
            f"📱 *Телефон:* `{data['phone']}`\n"
            f"📍 *Местоположение:* {map_url}\n"
            f"🚗 *Автомобиль:* {data['car_details']}\n"
            f"📝 *Описание ДТП:*\n{data['accident_details']}\n"
            f"📷 *Фотографий:* {len(data['photos'])}\n"
            f"🕒 *Время заявки:* {data['created_at']}\n"
            f"🆔 *ID пользователя:* {user.id}"
        )
        
        if data['username']:
            admin_message += f"\n👤 *Username:* @{data['username']}"
        
        # Отправляем администратору
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            # Отправляем фото если есть
            if data['photos']:
                for i, photo_id in enumerate(data['photos'][:5], 1):
                    try:
                        caption = f"Фото {i} от {data['full_name']}" if i == 1 else None
                        await context.bot.send_photo(
                            chat_id=ADMIN_CHAT_ID,
                            photo=photo_id,
                            caption=caption
                        )
                        await asyncio.sleep(0.3)  # Небольшая задержка между фото
                    except Exception as e:
                        logger.error(f"Ошибка отправки фото {i}: {e}")
        
        # Подтверждение пользователю
        await update.message.reply_text(
            "✅ *Заявка успешно отправлена!*\n\n"
            f"📞 *С вами свяжутся в течение 15 минут по номеру:* `{data['phone']}`\n\n"
            "Спасибо за обращение! 🚗\n\n"
            "Для новой заявки нажмите /start",
            reply_markup=get_start_keyboard(),
            parse_mode='Markdown'
        )
        
        # Очищаем данные
        del user_data_store[user.id]
        
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте еще раз с помощью /start",
            reply_markup=get_start_keyboard()
        )
    
    return ConversationHandler.END

# Отмена заявки
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in user_data_store:
        del user_data_store[user.id]
    
    await update.message.reply_text(
        "❌ Заявка отменена.\n\n"
        "Для новой заявки нажмите /start",
        reply_markup=get_start_keyboard()
    )
    
    return ConversationHandler.END

# Обработка команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 *Помощь по боту аварийного комиссара*\n\n"
        "Доступные команды:\n"
        "/start - Начать оформление заявки\n"
        "/help - Показать это сообщение\n\n"
        "После оформления заявки с вами свяжутся в течение 15 минут."
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_start_keyboard()
    )

# Основная функция
def main():
    # Проверяем наличие токена
    if not TOKEN:
        logger.error("❌ Токен бота не найден! Установите TELEGRAM_BOT_TOKEN")
        return
    
    logger.info("🚀 Запуск бота аварийного комиссара...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Настраиваем ConversationHandler с правильными фильтрами
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & filters.Regex('^🚀 Начать оформление заявки$'), start)
        ],
        states={
            PHONE: [
                MessageHandler(filters.CONTACT, handle_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                              lambda u, c: u.message.reply_text(
                                  "Пожалуйста, нажмите кнопку '📱 Отправить номер' для отправки контакта",
                                  reply_markup=get_contact_keyboard()
                              ))
            ],
            LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, 
                              lambda u, c: u.message.reply_text(
                                  "Пожалуйста, нажмите кнопку '📍 Отправить местоположение'",
                                  reply_markup=get_location_keyboard()
                              ))
            ],
            CAR_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^🚗 Уже заполнил данные$'), 
                              handle_car_details),
                MessageHandler(filters.TEXT & filters.Regex('^🚗 Уже заполнил данные$'), 
                              handle_car_details)
            ],
            ACCIDENT_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^📝 Уже заполнил описание$'), 
                              handle_accident_details),
                MessageHandler(filters.TEXT & filters.Regex('^📝 Уже заполнил описание$'), 
                              handle_accident_details)
            ],
            PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photos),
                MessageHandler(filters.TEXT & filters.Regex('^✅ Отправить заявку$'), send_application),
                MessageHandler(filters.TEXT & filters.Regex('^✅ Отправить заявку без фото$'), send_application),
                MessageHandler(filters.TEXT & filters.Regex('^📷 Прикрепить фото$'), handle_photos)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
            CommandHandler('help', help_command)
        ],
        allow_reentry=True
    )
    
    # Добавляем обработчики команд
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel))
    
    # Запускаем поллинг
    logger.info("🤖 Бот запущен в режиме polling...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False
    )

if __name__ == '__main__':
    main()

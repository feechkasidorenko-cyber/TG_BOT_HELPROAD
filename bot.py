import os
import logging
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
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')  # ID администратора

# Состояния для ConversationHandler
LOCATION, PHONE, CAR_DETAILS, ACCIDENT_DETAILS, PHOTOS, CONFIRMATION = range(6)

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

# Хранилище данных заявки (в production используйте БД)
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
    
    # Инициализируем данные пользователя
    user_data_store[user.id] = {
        'user_id': user.id,
        'username': user.username,
        'full_name': f"{user.first_name} {user.last_name or ''}",
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
    
    if user.id in user_data_store:
        user_data_store[user.id]['car_details'] = update.message.text
    
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
    
    if user.id in user_data_store:
        user_data_store[user.id]['accident_details'] = update.message.text
    
    await update.message.reply_text(
        "📝 Описание ДТП сохранено! Теперь прикрепите фотографии (до 5 фото).\n"
        "Отправьте по одной фотографии или несколько сразу.",
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
        
        # Сохраняем file_id фотографии
        user_data_store[user.id]['photos'].append(photo.file_id)
        
        photo_count = len(user_data_store[user.id]['photos'])
        
        if photo_count < 5:
            await update.message.reply_text(
                f"📷 Фотография #{photo_count} получена. "
                f"Можно отправить еще {5-photo_count} или нажмите '✅ Отправить заявку'",
                reply_markup=main_keyboard()
            )
        else:
            await update.message.reply_text(
                "✅ Максимальное количество фотографий достигнуто. "
                "Нажмите '✅ Отправить заявку' для завершения.",
                reply_markup=main_keyboard()
            )
    
    return PHOTOS

# Подтверждение и отправка заявки
async def send_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "⚠️ Заявка не найдена. Начните заново с /start",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END
    
    data = user_data_store[user.id]
    
    # Проверяем, что все обязательные поля заполнены
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
        f"🆔 ID пользователя: {user.id}\n"
        f"👤 Username: @{data['username'] if data['username'] else 'не указан'}"
    )
    
    try:
        # Отправляем сообщение администратору
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_message
            )
            
            # Отправляем фотографии администратору, если они есть
            if data['photos']:
                media_group = []
                for i, photo_id in enumerate(data['photos'][:5]):  # Максимум 5 фото
                    media_group.append({
                        'type': 'photo',
                        'media': photo_id,
                        'caption': f"Фото {i+1} от {data['full_name']}" if i == 0 else None
                    })
                
                if len(media_group) > 1:
                    await context.bot.send_media_group(
                        chat_id=ADMIN_CHAT_ID,
                        media=media_group
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=ADMIN_CHAT_ID,
                        photo=photo_id,
                        caption=f"Фото от {data['full_name']}"
                    )
        
        # Подтверждение пользователю
        await update.message.reply_text(
            "✅ Заявка успешно отправлена!\n\n"
            "📞 С вами свяжутся в течение 15 минут.\n"
            "Ожидайте звонка по номеру: " + data['phone'] + "\n\n"
            "Для новой заявки нажмите /start",
            reply_markup=ReplyKeyboardMarkup([['/start']], resize_keyboard=True)
        )
        
        # Очищаем данные пользователя
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

# Команда для админа - просмотр всех заявок
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем, что команду вызвал админ
    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    active_requests = len(user_data_store)
    
    await update.message.reply_text(
        f"📊 Статистика бота:\n"
        f"• Активных заявок: {active_requests}\n"
        f"• Всего пользователей в базе: {len(user_data_store)}\n\n"
        f"Для просмотра заявок используйте ID пользователя."
    )

# Основная функция
def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Настраиваем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: update.message.reply_text("Пожалуйста, отправьте местоположение", reply_markup=main_keyboard()))
            ],
            PHONE: [
                MessageHandler(filters.CONTACT, handle_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: update.message.reply_text("Пожалуйста, отправьте номер телефона", reply_markup=main_keyboard()))
            ],
            CAR_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_car_details)
            ],
            ACCIDENT_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accident_details)
            ],
            PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photos),
                MessageHandler(filters.TEXT & filters.Regex('^✅ Отправить заявку$'), send_application)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start)
        ]
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("admin", admin_stats))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Запускаем бота
    port = int(os.environ.get('PORT', 8443))
    
    if TOKEN:
        print(f"Бот запущен на порту {port}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TOKEN,
            webhook_url=f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com/{TOKEN}"
        )
    else:
        print("Токен не найден!")

if __name__ == '__main__':
    main()

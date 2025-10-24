from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Optional
import asyncio
import base64
import sqlite3
from loguru import logger

from src.database.simple_db import db
from src.services.gemini_service import ReplicateImageService
from src.services.yookassa_service import get_yookassa_service
from config import SUBSCRIPTION_PLANS

# Создаем экземпляр сервиса
replicate_service = ReplicateImageService()

# Состояния для FSM
class ImageStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_edit_prompt = State()
    waiting_for_style = State()
    waiting_for_image = State()

# Роутер для обработчиков
router = Router()

# Клавиатуры
def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Генерировать изображение", callback_data="generate_image")],
        [InlineKeyboardButton(text="✏️ Редактировать изображение", callback_data="edit_image")],
        [InlineKeyboardButton(text="💎 Моя подписка", callback_data="subscription")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])

def get_subscription_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Выбрать план", callback_data="select_plan")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def get_plans_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора планов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 1 месяц - 999₽", callback_data="plan_1_month")],
        [InlineKeyboardButton(text="📅 3 месяца - 1499₽", callback_data="plan_3_months")],
        [InlineKeyboardButton(text="📅 1 год - 4999₽", callback_data="plan_1_year")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="subscription")]
    ])

def get_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Художественный", callback_data="style_artistic")],
        [InlineKeyboardButton(text="📸 Фотореалистичный", callback_data="style_photorealistic")],
        [InlineKeyboardButton(text="🎭 Мультяшный", callback_data="style_cartoon")],
        [InlineKeyboardButton(text="📺 Винтажный", callback_data="style_vintage")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "User"
    
    # Проверяем, есть ли пользователь в базе
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, username, first_name)
        logger.info(f"New user registered: {user_id}")
    
    welcome_text = f"""
🎨 <b>Добро пожаловать в Gemini Image Editor!</b>

Привет, {first_name}! Я помогу тебе создавать и редактировать изображения с помощью искусственного интеллекта Google Gemini.

<b>Возможности:</b>
• 🎨 Генерация изображений по текстовому описанию
• ✏️ Редактирование существующих изображений
• 🎭 Создание вариаций в разных стилях
• 📝 Улучшение описаний изображений

<b>Для доступа к функциям нужна подписка.</b>

Выбери действие:
    """
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    await state.clear()

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
<b>📖 Справка по использованию бота</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка
/subscription - Информация о подписке

<b>Как пользоваться:</b>

1️⃣ <b>Генерация изображения:</b>
• Нажми "🎨 Генерировать изображение"
• Опиши, что хочешь создать
• Получи детальное описание для создания изображения

2️⃣ <b>Редактирование изображения:</b>
• Нажми "✏️ Редактировать изображение"
• Отправь изображение
• Опиши, какие изменения нужны
• Получи инструкции по редактированию

3️⃣ <b>Стили изображений:</b>
• Художественный - живописный стиль
• Фотореалистичный - как фотография
• Мультяшный - аниме/мультфильм
• Винтажный - ретро стиль

<b>💎 Подписка:</b>
• Доступ ко всем функциям на 30 дней
• Безлимитная генерация и редактирование
• Приоритетная поддержка

<b>❓ Поддержка:</b>
Если возникли вопросы, напиши @your_support_username
    """
    
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    """Обработчик команды /subscription"""
    user_id = message.from_user.id
    await show_subscription_info(message, user_id)

@router.message(Command("admin_activate"))
async def cmd_admin_activate(message: Message):
    """Админ-команда для активации подписки (временное решение)"""
    user_id = message.from_user.id
    text = message.text or ""
    
    # Список админов
    admin_ids = [95714127, 888641250, 369631340]  # Список всех админов
    if user_id not in admin_ids:
        await message.answer("❌ Доступ запрещен")
        return
    
    # Проверяем, указан ли ID пользователя в команде
    # Формат: /admin_activate 123456789
    target_user_id = user_id  # По умолчанию активируем для себя
    
    if len(text.split()) > 1:
        try:
            target_user_id = int(text.split()[1])
        except ValueError:
            await message.answer("❌ Неверный формат. Используйте: /admin_activate [ID_пользователя]")
            return
    
    # Активируем подписку на 30 дней
    success = await db.create_subscription(
        telegram_id=target_user_id,
        plan_name="1_month",
        price=999,
        duration_days=30,
        payment_id=f"admin_activation_{target_user_id}"
    )
    
    if success:
        if target_user_id == user_id:
            await message.answer("✅ Подписка активирована на 30 дней")
        else:
            await message.answer(f"✅ Подписка активирована для пользователя {target_user_id} на 30 дней")
        logger.success(f"Admin subscription activated for user {target_user_id}")
    else:
        await message.answer("❌ Ошибка активации подписки")
        logger.error(f"Failed to activate admin subscription for user {target_user_id}")

@router.message(Command("admin_status"))
async def cmd_admin_status(message: Message):
    """Админ-команда для проверки статуса подписки"""
    user_id = message.from_user.id
    
    # Список админов
    admin_ids = [95714127, 888641250, 369631340]  # Список всех админов
    if user_id not in admin_ids:
        await message.answer("❌ Доступ запрещен")
        return
    
    # Проверяем подписку
    subscription_active = await db.check_subscription(user_id)
    subscription_info = await db.get_subscription_info(user_id)
    
    if subscription_active and subscription_info:
        await message.answer(
            f"✅ <b>Подписка активна</b>\n\n"
            f"📅 План: {subscription_info['plan']}\n"
            f"⏰ Истекает: {subscription_info['expires_at']}\n"
            f"🔄 Статус: {'Активна' if subscription_info['is_active'] else 'Неактивна'}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Подписка не активна")

@router.message(Command("admin_activate_cillsssu"))
async def cmd_admin_activate_cillsssu(message: Message):
    """Специальная команда для активации подписки пользователя cillsssu"""
    user_id = message.from_user.id
    
    # Список админов
    admin_ids = [95714127, 888641250, 369631340]  # Список всех админов
    if user_id not in admin_ids:
        await message.answer("❌ Доступ запрещен")
        return
    
    # Активируем подписку для пользователя 888641250
    success = await db.create_subscription(
        telegram_id=888641250,
        plan_name="1_month",
        price=999,
        duration_days=30,
        payment_id="admin_activation_cillsssu"
    )
    
    if success:
        await message.answer("✅ Подписка активирована для пользователя cillsssu (888641250) на 30 дней")
        logger.success(f"Admin subscription activated for user 888641250")
    else:
        await message.answer("❌ Ошибка активации подписки")
        logger.error(f"Failed to activate admin subscription for user 888641250")

@router.message(Command("admin_activate_rakhim"))
async def cmd_admin_activate_rakhim(message: Message):
    """Специальная команда для активации подписки пользователя RakhimPS"""
    user_id = message.from_user.id
    
    # Список админов
    admin_ids = [95714127, 888641250, 369631340]  # Список всех админов
    if user_id not in admin_ids:
        await message.answer("❌ Доступ запрещен")
        return
    
    # Активируем подписку для пользователя 7948329307
    success = await db.create_subscription(
        telegram_id=7948329307,
        plan_name="1_month",
        price=999,
        duration_days=30,
        payment_id="admin_activation_rakhim"
    )
    
    if success:
        await message.answer("✅ Подписка активирована для пользователя RakhimPS (7948329307) на 30 дней")
        logger.success(f"Admin subscription activated for user 7948329307")
    else:
        await message.answer("❌ Ошибка активации подписки")
        logger.error(f"Failed to activate admin subscription for user 7948329307")

@router.message(Command("admin_deactivate"))
async def cmd_admin_deactivate(message: Message):
    """Админ-команда для деактивации подписки"""
    user_id = message.from_user.id
    
    # Список админов
    admin_ids = [95714127, 888641250, 369631340]  # Список всех админов
    if user_id not in admin_ids:
        await message.answer("❌ Доступ запрещен")
        return
    
    # Деактивируем подписку
    try:
        conn = sqlite3.connect("bot_subscriptions.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET subscription_active = FALSE 
            WHERE telegram_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        await message.answer("✅ Подписка деактивирована")
        logger.success(f"Admin subscription deactivated for user {user_id}")
        
    except Exception as e:
        await message.answer("❌ Ошибка деактивации подписки")
        logger.error(f"Error deactivating admin subscription: {e}")

# Обработчики callback-запросов
@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    try:
        await callback.message.edit_text(
            "🎨 <b>Главное меню</b>\n\nВыбери действие:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except:
        await callback.message.answer(
            "🎨 <b>Главное меню</b>\n\nВыбери действие:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "generate_image")
async def callback_generate_image(callback: CallbackQuery, state: FSMContext):
    """Начать генерацию изображения"""
    user_id = callback.from_user.id
    
    # Проверяем подписку
    subscription_active = await db.check_subscription(user_id)
    if not subscription_active:
        await callback.message.edit_text(
            "❌ <b>Требуется подписка</b>\n\nДля генерации изображений нужна активная подписка.",
            reply_markup=get_subscription_keyboard(user_id),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    try:
        await callback.message.edit_text(
            "🎨 <b>Генерация изображения</b>\n\nОпиши, какое изображение ты хочешь создать. "
            "Будь максимально подробным в описании:\n\n"
            "• Объекты и персонажи\n"
            "• Цвета и освещение\n"
            "• Стиль и настроение\n"
            "• Композиция\n\n"
            "Например: \"Красивый закат над морем с силуэтом парусника, теплые оранжевые и розовые тона, романтическое настроение\"",
            parse_mode="HTML"
        )
    except:
        # Если не можем редактировать, отправляем новое сообщение
        await callback.message.answer(
            "🎨 <b>Генерация изображения</b>\n\nОпиши, какое изображение ты хочешь создать. "
            "Будь максимально подробным в описании:\n\n"
            "• Объекты и персонажи\n"
            "• Цвета и освещение\n"
            "• Стиль и настроение\n"
            "• Композиция\n\n"
            "Например: \"Красивый закат над морем с силуэтом парусника, теплые оранжевые и розовые тона, романтическое настроение\"",
            parse_mode="HTML"
        )
    
    await state.set_state(ImageStates.waiting_for_prompt)
    await callback.answer()

@router.callback_query(F.data == "edit_image")
async def callback_edit_image(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование изображения"""
    user_id = callback.from_user.id
    
    # Проверяем подписку
    subscription_active = await db.check_subscription(user_id)
    if not subscription_active:
        try:
            await callback.message.edit_text(
                "❌ <b>Требуется подписка</b>\n\nДля редактирования изображений нужна активная подписка.",
                reply_markup=get_subscription_keyboard(user_id),
                parse_mode="HTML"
            )
        except:
            await callback.message.answer(
                "❌ <b>Требуется подписка</b>\n\nДля редактирования изображений нужна активная подписка.",
                reply_markup=get_subscription_keyboard(user_id),
                parse_mode="HTML"
            )
        await callback.answer()
        return
    
    try:
        await callback.message.edit_text(
            "✏️ <b>Редактирование изображения</b>\n\n"
            "📸 <b>Шаг 1:</b> Отправь изображение, которое хочешь отредактировать\n"
            "✍️ <b>Шаг 2:</b> Напиши, какие изменения внести\n\n"
            "Можешь отправить:\n"
            "• Свое фото из галереи\n"
            "• Сгенерированное изображение",
            parse_mode="HTML"
        )
    except:
        await callback.message.answer(
            "✏️ <b>Редактирование изображения</b>\n\n"
            "📸 <b>Шаг 1:</b> Отправь изображение, которое хочешь отредактировать\n"
            "✍️ <b>Шаг 2:</b> Напиши, какие изменения внести\n\n"
            "Можешь отправить:\n"
            "• Свое фото из галереи\n"
            "• Сгенерированное изображение",
            parse_mode="HTML"
        )
    
    # Устанавливаем состояние ожидания изображения
    await state.set_state(ImageStates.waiting_for_image)
    await callback.answer()

@router.callback_query(F.data == "subscription")
async def callback_subscription(callback: CallbackQuery):
    """Информация о подписке"""
    user_id = callback.from_user.id
    await show_subscription_info(callback.message, user_id)
    await callback.answer()

@router.callback_query(F.data == "select_plan")
async def callback_select_plan(callback: CallbackQuery):
    """Выбор плана подписки"""
    try:
        await callback.message.edit_text(
            "💎 <b>Выбери план подписки</b>\n\n"
            "Все планы включают:\n"
            "• 🎨 Генерация изображений\n"
            "• ✏️ Редактирование изображений\n"
            "• 🎭 Создание вариаций\n"
            "• 📝 Улучшение описаний\n"
            "• ⚡ Приоритетная обработка\n\n"
            "Выбери подходящий план:",
            reply_markup=get_plans_keyboard(),
            parse_mode="HTML"
        )
    except:
        await callback.message.answer(
            "💎 <b>Выбери план подписки</b>\n\n"
            "Все планы включают:\n"
            "• 🎨 Генерация изображений\n"
            "• ✏️ Редактирование изображений\n"
            "• 🎭 Создание вариаций\n"
            "• 📝 Улучшение описаний\n"
            "• ⚡ Приоритетная обработка\n\n"
            "Выбери подходящий план:",
            reply_markup=get_plans_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("plan_"))
async def callback_buy_plan(callback: CallbackQuery):
    """Покупка конкретного плана"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    plan_type = callback.data.replace("plan_", "")
    
    if plan_type not in SUBSCRIPTION_PLANS:
        await callback.answer("❌ Неверный план", show_alert=True)
        return
    
    plan = SUBSCRIPTION_PLANS[plan_type]
    
    # Создаем платеж через ЮKassa
    payment_data = await get_yookassa_service().create_payment(
        user_id=user_id,
        plan_type=plan_type,
        description=f"Подписка Gemini Image Editor - {plan['name']}"
    )
    
    if payment_data:
        payment_url = get_yookassa_service().get_payment_url(payment_data)
        
        if payment_url:
            try:
                await callback.message.edit_text(
                    f"💳 <b>Оплата подписки</b>\n\n"
                    f"План: {plan['name']}\n"
                    f"Цена: {plan['price']}₽\n"
                    f"Длительность: {plan['duration_days']} дней\n\n"
                    f"Нажми на ссылку ниже для оплаты:\n"
                    f"{payment_url}\n\n"
                    f"После успешной оплаты твоя подписка будет активирована автоматически.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к планам", callback_data="select_plan")]
                    ]),
                    parse_mode="HTML"
                )
            except:
                await callback.message.answer(
                    f"💳 <b>Оплата подписки</b>\n\n"
                    f"План: {plan['name']}\n"
                    f"Цена: {plan['price']}₽\n"
                    f"Длительность: {plan['duration_days']} дней\n\n"
                    f"Нажми на ссылку ниже для оплаты:\n"
                    f"{payment_url}\n\n"
                    f"После успешной оплаты твоя подписка будет активирована автоматически.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к планам", callback_data="select_plan")]
                    ]),
                    parse_mode="HTML"
                )
        else:
            try:
                await callback.message.edit_text(
                    "❌ <b>Ошибка</b>\n\nНе удалось получить ссылку для оплаты. Попробуй позже.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к планам", callback_data="select_plan")]
                    ]),
                    parse_mode="HTML"
                )
            except:
                await callback.message.answer(
                    "❌ <b>Ошибка</b>\n\nНе удалось получить ссылку для оплаты. Попробуй позже.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к планам", callback_data="select_plan")]
                    ]),
                    parse_mode="HTML"
                )
    else:
        try:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\nНе удалось создать платеж. Попробуй позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к планам", callback_data="select_plan")]
                ]),
                parse_mode="HTML"
            )
        except:
            await callback.message.answer(
                "❌ <b>Ошибка</b>\n\nНе удалось создать платеж. Попробуй позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад к планам", callback_data="select_plan")]
                ]),
                parse_mode="HTML"
            )
    
    await callback.answer()

@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Показать справку"""
    await cmd_help(callback.message)
    await callback.answer()

# Обработчики состояний
@router.message(ImageStates.waiting_for_prompt)
async def process_prompt(message: Message, state: FSMContext):
    """Обработка промпта для генерации"""
    user_id = message.from_user.id
    prompt = message.text
    
    if not prompt or len(prompt) < 10:
        await message.answer(
            "❌ Промпт слишком короткий. Опиши изображение более подробно (минимум 10 символов)."
        )
        return
    
    # Показываем анимацию загрузки
    processing_msg = await message.answer("🎨 <b>Генерация изображения...</b>\n\n⏳ Пожалуйста, подождите...")
    
    try:
        # Генерируем изображение через Replicate API
        image_url = await replicate_service.generate_image(prompt, user_id)
        
        if image_url:
            # Это реальное изображение - отправляем по URL
            try:
                await processing_msg.delete()
            except:
                pass  # Игнорируем ошибку если сообщение уже удалено
            
            # Логируем успешную генерацию
            await db.log_image_generation(user_id, prompt, True, image_url)
            
            # Сохраняем URL изображения в состоянии для редактирования
            await state.update_data(last_image_url=image_url)
            
            # Отправляем изображение по URL
            await message.answer_photo(
                photo=image_url,
                caption=f"🎨 <b>Сгенерированное изображение:</b>\n\n<i>{prompt}</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎨 Создать еще", callback_data="generate_image")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]),
                parse_mode="HTML"
            )
        else:
            try:
                await processing_msg.edit_text(
                    "❌ Не удалось сгенерировать описание. Попробуй еще раз с другим промптом.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ])
                )
            except:
                await message.answer(
                    "❌ Не удалось сгенерировать описание. Попробуй еще раз с другим промптом.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ])
                )
            
            # Логируем неудачную генерацию
            await db.log_image_generation(user_id, prompt, False)
    
    except Exception as e:
        logger.error(f"Error processing prompt: {e}")
        try:
            await processing_msg.edit_text(
                "❌ Произошла ошибка при генерации. Попробуй позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ])
            )
        except:
            await message.answer(
                "❌ Произошла ошибка при генерации. Попробуй позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ])
            )
    
    await state.clear()

@router.message(ImageStates.waiting_for_image, F.photo)
async def process_image_for_edit(message: Message, state: FSMContext):
    """Обработка изображения для редактирования"""
    user_id = message.from_user.id
    logger.info(f"Photo received for user {user_id}")
    
    # Получаем изображение
    photo = message.photo[-1]  # Берем самое большое разрешение
    file = await message.bot.get_file(photo.file_id)
    logger.info(f"File info: {file.file_path}")
    
    # Получаем URL изображения от Telegram
    image_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
    
    # Сохраняем URL изображения в состоянии
    await state.update_data(last_image_url=image_url)
    logger.info(f"Image URL saved to state: {image_url}")
    
    await message.answer(
        "✏️ <b>Редактирование изображения</b>\n\n"
        "Отлично! Теперь опиши, какие изменения ты хочешь внести в изображение:\n\n"
        "• Изменить цвета\n"
        "• Добавить или убрать объекты\n"
        "• Изменить стиль\n"
        "• Добавить эффекты\n\n"
        "Например: \"Сделать изображение в черно-белом стиле с добавлением дождя\"",
        parse_mode="HTML"
    )
    
    # Переходим к состоянию ожидания промпта
    await state.set_state(ImageStates.waiting_for_edit_prompt)
    logger.info(f"State changed to waiting_for_edit_prompt for user {user_id}")

@router.message(ImageStates.waiting_for_image)
async def process_text_instead_of_image(message: Message, state: FSMContext):
    """Обработка текста вместо изображения"""
    logger.info(f"Text received in waiting_for_image state: {message.text}")
    await message.answer(
        "❌ <b>Сначала отправь изображение!</b>\n\n"
        "📸 <b>Шаг 1:</b> Отправь изображение, которое хочешь отредактировать\n"
        "✍️ <b>Шаг 2:</b> Потом напиши, какие изменения внести\n\n"
        "Можешь отправить:\n"
        "• Свое фото из галереи\n"
        "• Сгенерированное изображение",
        parse_mode="HTML"
    )

@router.message(ImageStates.waiting_for_edit_prompt)
async def process_edit_prompt(message: Message, state: FSMContext):
    """Обработка промпта для редактирования"""
    user_id = message.from_user.id
    edit_prompt = message.text
    
    if not edit_prompt or len(edit_prompt) < 5:
        await message.answer("❌ Описание изменений слишком короткое. Опиши подробнее.")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    logger.info(f"Edit prompt data: {data}")
    last_image_url = data.get('last_image_url')
    logger.info(f"Last image URL: {last_image_url}")
    
    if not last_image_url:
        await message.answer("❌ Изображение не найдено. Начни заново.")
        await state.clear()
        return
    
    # Показываем, что обрабатываем
    processing_msg = await message.answer("🔄 Редактирую изображение...")
    
    try:
        # Получаем URL изображения из состояния (может быть сгенерированное или пользовательское)
        if not last_image_url:
            await message.answer(
                "❌ <b>Нет изображения для редактирования</b>\n\n"
                "Сначала отправьте изображение или сгенерируйте его, а затем попробуйте отредактировать.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎨 Генерировать изображение", callback_data="generate_image")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ]),
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Редактируем изображение через Replicate API
        edited_image_url = await replicate_service.edit_image(edit_prompt, last_image_url)
        
        if edited_image_url:
            # Отправляем отредактированное изображение по URL
            try:
                await processing_msg.delete()
            except:
                pass  # Игнорируем ошибку если сообщение уже удалено
            
            await message.answer_photo(
                photo=edited_image_url,
                caption=f"✏️ <b>Отредактированное изображение</b>\n\n<i>Запрос: {edit_prompt}</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✏️ Редактировать еще", callback_data="edit_image")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ])
            )
        else:
            try:
                await processing_msg.edit_text(
                    "❌ <b>Не удалось отредактировать изображение</b>\n\n"
                    "🚫 <b>Возможные причины:</b>\n"
                    "• Изображение содержит чувствительный контент\n"
                    "• Промпт содержит неподходящие слова\n"
                    "• Проблемы с API\n\n"
                    "💡 <b>Попробуйте:</b>\n"
                    "• Другое изображение\n"
                    "• Более нейтральный промпт\n"
                    "• Изменить стиль или цвета",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ Попробовать снова", callback_data="edit_image")],
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ]),
                    parse_mode="HTML"
                )
            except:
                await message.answer(
                    "❌ <b>Не удалось отредактировать изображение</b>\n\n"
                    "🚫 <b>Возможные причины:</b>\n"
                    "• Изображение содержит чувствительный контент\n"
                    "• Промпт содержит неподходящие слова\n"
                    "• Проблемы с API\n\n"
                    "💡 <b>Попробуйте:</b>\n"
                    "• Другое изображение\n"
                    "• Более нейтральный промпт\n"
                    "• Изменить стиль или цвета",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✏️ Попробовать снова", callback_data="edit_image")],
                        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                    ]),
                    parse_mode="HTML"
                )
    
    except Exception as e:
        logger.error(f"Error processing edit: {e}")
        try:
            await processing_msg.edit_text(
                "❌ Произошла ошибка при обработке. Попробуй позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ])
            )
        except:
            await message.answer(
                "❌ Произошла ошибка при обработке. Попробуй позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                ])
            )
    
    await state.clear()

# Вспомогательные функции
async def show_subscription_info(message: Message, user_id: int):
    """Показать информацию о подписке"""
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    
    subscription_active = await db.check_subscription(user_id)
    
    if subscription_active:
        expires_at = user.get('subscription_expires_at')
        plan_type = user.get('subscription_plan', 'unknown')
        plan_name = SUBSCRIPTION_PLANS.get(plan_type, {}).get('name', 'Неизвестный план')
        
        if expires_at:
            from datetime import datetime, timezone
            # Поддержка как строк ISO, так и datetime
            if isinstance(expires_at, str):
                expires_date = datetime.fromisoformat(expires_at)
            else:
                expires_date = expires_at
            # Нормализуем к локальному формату (оставляем как есть, если tz-aware)
            expires_str = expires_date.strftime("%d.%m.%Y %H:%M")
        else:
            expires_str = "Неизвестно"
        
        text = f"""
💎 <b>Твоя подписка активна!</b>

✅ Статус: Активна
📋 План: {plan_name}
📅 Действует до: {expires_str}

<b>Доступные функции:</b>
• 🎨 Генерация изображений
• ✏️ Редактирование изображений
• 🎭 Создание вариаций
• 📝 Улучшение описаний
• ⚡ Приоритетная обработка
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
    else:
        text = f"""
💎 <b>Информация о подписке</b>

❌ Статус: Неактивна

<b>Что дает подписка:</b>
• 🎨 Генерация изображений по описанию
• ✏️ Редактирование существующих изображений
• 🎭 Создание вариаций в разных стилях
• 📝 Улучшение описаний изображений
• ⚡ Приоритетная обработка

<b>Доступные планы:</b>
• 📅 1 месяц - 999₽
• 📅 3 месяца - 1499₽ (экономия 25%)
• 📅 1 год - 4999₽ (экономия 58%)
        """
        
        keyboard = get_subscription_keyboard(user_id)
    
    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        # Если не можем редактировать, отправляем новое сообщение
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

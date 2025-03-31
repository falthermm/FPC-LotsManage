from typing import TYPE_CHECKING, Dict, List
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import logging
from telebot import types

if TYPE_CHECKING:
    from cardinal import Cardinal
else:
    from cardinal import Cardinal  # Добавляем импорт Cardinal

logger = logging.getLogger("FPC.DevLotFL")

NAME = "DevLotFL"
VERSION = "0.0.1"
DESCRIPTION = """🎮 Плагин для управления лотами на FunPay

Возможности:
• Добавление/удаление лотов
• Активация/деактивация лотов
• Управление через Telegram"""

AUTHOR = "@ssswwwi"
CREDITS = "@ssswwwi"
UUID = "f3accbd0-27fc-4bf7-9dc3-0e88c8e2c69f"
SETTINGS_PAGE = False
BIND_TO_NEW_MESSAGE = []
BIND_TO_DELETE = None

LOTS_CONFIG_FILE = f"storage/plugins/{UUID}/lots_config.json"

# Загрузка и сохранение конфигурации лотов
def load_lots_config() -> dict:
    if os.path.exists(LOTS_CONFIG_FILE):
        with open(LOTS_CONFIG_FILE, "r", encoding='utf-8') as file:
            return json.load(file)
    return {"active_lots": [], "inactive_lots": []}

def save_lots_config(config: dict) -> None:
    os.makedirs(f"storage/plugins/{UUID}", exist_ok=True)
    with open(LOTS_CONFIG_FILE, "w", encoding='utf-8') as file:
        json.dump(config, file, indent=4, ensure_ascii=False)

def add_lot(lot_id: str, active: bool = True) -> bool:
    config = load_lots_config()
    target_list = "active_lots" if active else "inactive_lots"
    
    if lot_id in config["active_lots"] or lot_id in config["inactive_lots"]:
        return False
        
    config[target_list].append(lot_id)
    save_lots_config(config)
    return True

def remove_lot(lot_id: str) -> bool:
    config = load_lots_config()
    
    if lot_id in config["active_lots"]:
        config["active_lots"].remove(lot_id)
        save_lots_config(config)
        return True
    elif lot_id in config["inactive_lots"]:
        config["inactive_lots"].remove(lot_id)
        save_lots_config(config)
        return True
    return False

def toggle_lot_status(lot_id: str) -> bool:
    config = load_lots_config()
    
    if lot_id in config["active_lots"]:
        config["active_lots"].remove(lot_id)
        config["inactive_lots"].append(lot_id)
        save_lots_config(config)
        return True
    elif lot_id in config["inactive_lots"]:
        config["inactive_lots"].remove(lot_id)
        config["active_lots"].append(lot_id)
        save_lots_config(config)
        return True
    return False

def activate_lots(c: Cardinal, lot_ids: List[str]) -> Dict[str, List]:
    result = {
        "activated": [],
        "already_active": [], 
        "not_found": [],
        "errors": []
    }
    
    for lot_id in lot_ids:
        try:
            fields = c.account.get_lot_fields(int(lot_id))
            if fields is None:
                result["not_found"].append(lot_id)
                continue
                
            if fields.active:
                result["already_active"].append(lot_id) 
                continue
                
            fields.active = True
            c.account.save_lot(fields)
            result["activated"].append(lot_id)
            
        except Exception as e:
            result["errors"].append((lot_id, str(e)))
            
    return result

def deactivate_lots(c: Cardinal, lot_ids: List[str]) -> Dict[str, List]:
    result = {
        "deactivated": [],
        "already_inactive": [],
        "not_found": [],
        "errors": []
    }
    
    for lot_id in lot_ids:
        try:
            fields = c.account.get_lot_fields(int(lot_id))
            if fields is None:
                result["not_found"].append(lot_id)
                continue
                
            if not fields.active:
                result["already_inactive"].append(lot_id)
                continue
                
            fields.active = False
            c.account.save_lot(fields)
            result["deactivated"].append(lot_id)
            
        except Exception as e:
            result["errors"].append((lot_id, str(e)))
            
    return result

def init_commands(cardinal: Cardinal, *args):
    if not cardinal.telegram:
        return
        
    tg = cardinal.telegram
    bot = tg.bot

    def get_lots_keyboard():
        keyboard = InlineKeyboardMarkup(row_width=2)
        add_lot = InlineKeyboardButton("➕ Добавить лот", callback_data='add_lot')
        remove_lot = InlineKeyboardButton("➖ Удалить лот", callback_data='remove_lot')
        toggle_lot = InlineKeyboardButton("🔄 Изменить статус", callback_data='toggle_lot')
        view_lots = InlineKeyboardButton("📋 Список лотов", callback_data='view_lots')
        
        keyboard.row(add_lot, remove_lot)
        keyboard.add(toggle_lot)
        keyboard.add(view_lots)
        return keyboard

    def send_lots_menu(m: types.Message):
        bot.reply_to(
            m,
            f"📦 Управление лотами {NAME} v{VERSION}:",
            reply_markup=get_lots_keyboard()
        )

    def handle_callback(call: types.CallbackQuery):
        if call.data == 'add_lot':
            back_button = InlineKeyboardButton("❌ Отмена", callback_data='cancel')
            kb = InlineKeyboardMarkup().add(back_button)
            result = bot.send_message(
                call.message.chat.id,
                "Введите ID лота для добавления:",
                reply_markup=kb
            )
            tg.set_state(
                chat_id=call.message.chat.id,
                message_id=result.id,
                user_id=call.from_user.id,
                state="adding_lot"
            )

        elif call.data == 'remove_lot':
            config = load_lots_config()
            all_lots = config["active_lots"] + config["inactive_lots"]
            
            if not all_lots:
                bot.answer_callback_query(call.id, "Список лотов пуст!")
                return
                
            keyboard = InlineKeyboardMarkup(row_width=2)
            for lot_id in all_lots:
                status = "🟢" if lot_id in config["active_lots"] else "🔴"
                keyboard.add(InlineKeyboardButton(
                    f"{status} Лот {lot_id}",
                    callback_data=f'remove_lot_{lot_id}'
                ))
            keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu'))
            
            bot.edit_message_text(
                "Выберите лот для удаления:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )

        elif call.data.startswith('remove_lot_'):
            lot_id = call.data.replace('remove_lot_', '')
            if remove_lot(lot_id):
                bot.answer_callback_query(call.id, f"Лот {lot_id} удален!")
            else:
                bot.answer_callback_query(call.id, "Ошибка при удалении лота!")
                
            bot.edit_message_text(
                f"📦 Управление лотами {NAME} v{VERSION}:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_lots_keyboard()
            )

        elif call.data == 'toggle_lot':
            config = load_lots_config()
            all_lots = config["active_lots"] + config["inactive_lots"]
            
            if not all_lots:
                bot.answer_callback_query(call.id, "Список лотов пуст!")
                return
                
            keyboard = InlineKeyboardMarkup(row_width=2)
            for lot_id in all_lots:
                status = "🟢" if lot_id in config["active_lots"] else "🔴"
                keyboard.add(InlineKeyboardButton(
                    f"{status} Лот {lot_id}",
                    callback_data=f'toggle_lot_{lot_id}'
                ))
            keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu'))
            
            bot.edit_message_text(
                "Выберите лот для изменения статуса:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )

        elif call.data.startswith('toggle_lot_'):
            lot_id = call.data.replace('toggle_lot_', '')
            config = load_lots_config()
            
            if lot_id in config["active_lots"]:
                # Деактивируем лот на FunPay
                result = deactivate_lots(cardinal, [lot_id])
                if result["deactivated"]:
                    config["active_lots"].remove(lot_id)
                    config["inactive_lots"].append(lot_id)
                    save_lots_config(config)
                    status_text = "деактивирован"
                elif result["errors"]:
                    bot.answer_callback_query(call.id, f"Ошибка: {result['errors'][0][1]}")
                    return
            else:
                # Активируем лот на FunPay
                result = activate_lots(cardinal, [lot_id])
                if result["activated"]:
                    config["inactive_lots"].remove(lot_id) 
                    config["active_lots"].append(lot_id)
                    save_lots_config(config)
                    status_text = "активирован"
                elif result["errors"]:
                    bot.answer_callback_query(call.id, f"Ошибка: {result['errors'][0][1]}")
                    return
                    
            bot.answer_callback_query(call.id, f"Лот {lot_id} успешно {status_text}!")
            
            bot.edit_message_text(
                f"📦 Управление лотами {NAME} v{VERSION}:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_lots_keyboard()
            )

        elif call.data == 'view_lots':
            config = load_lots_config()
            active_lots = config["active_lots"]
            inactive_lots = config["inactive_lots"]
            
            message = "📋 Список лотов:\n\n"
            if active_lots:
                message += "🟢 Активные лоты:\n"
                for lot in active_lots:
                    message += f"• {lot}\n"
            if inactive_lots:
                message += "\n🔴 Неактивные лоты:\n"
                for lot in inactive_lots:
                    message += f"• {lot}\n"
            if not active_lots and not inactive_lots:
                message += "Список лотов пуст"
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu'))
            
            bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )

        elif call.data == 'back_to_menu':
            bot.edit_message_text(
                f"📦 Управление лотами {NAME} v{VERSION}:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_lots_keyboard()
            )

        elif call.data == 'cancel':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            tg.clear_state(call.message.chat.id, call.from_user.id)

        bot.answer_callback_query(call.id)

    def handle_text_input(message: types.Message):
        state_data = tg.get_state(message.chat.id, message.from_user.id)
        if state_data and state_data.get('state') == 'adding_lot':
            try:
                lot_id = message.text.strip()
                if not lot_id.isdigit():
                    bot.send_message(
                        message.chat.id,
                        "❌ ID лота должен быть числом"
                    )
                    return
                    
                fields = cardinal.account.get_lot_fields(int(lot_id))
                if fields is None:
                    bot.send_message(
                        message.chat.id,
                        "❌ Лот с таким ID не найден на FunPay"
                    )
                    return
                
                if add_lot(lot_id):
                    result = activate_lots(cardinal, [lot_id])
                    if result["activated"]:
                        success_msg = f"✅ Лот {lot_id} успешно добавлен и активирован"
                    elif result["already_active"]:
                        success_msg = f"✅ Лот {lot_id} добавлен (уже был активен)"
                    else:
                        success_msg = f"⚠️ Лот {lot_id} добавлен, но возникла ошибка при активации"
                    
                    bot.send_message(
                        message.chat.id,
                        success_msg
                    )
                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ Лот {lot_id} уже существует в списке"
                    )
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    f"❌ Ошибка при добавлении лота: {str(e)}"
                )
            finally:
                tg.clear_state(message.chat.id, message.from_user.id)
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.delete_message(message.chat.id, message.message_id - 1)
                except:
                    pass

    tg.msg_handler(send_lots_menu, commands=["lots"])
    tg.cbq_handler(
        handle_callback,
        lambda c: c.data in [
            'add_lot', 'remove_lot', 'toggle_lot', 'view_lots',
            'back_to_menu', 'cancel'
        ] or c.data.startswith(('remove_lot_', 'toggle_lot_'))
    )
    tg.msg_handler(
        handle_text_input,
        func=lambda m: tg.check_state(m.chat.id, m.from_user.id, "adding_lot")
    )

    cardinal.add_telegram_commands(UUID, [
        ("lots", "управление лотами", True)
    ])

logger.info(f"Загружен {NAME} ({VERSION})")

BIND_TO_PRE_INIT = [init_commands]
BIND_TO_POST_INIT = []
BIND_TO_NEW_MESSAGE = []
BIND_TO_DELETE = None
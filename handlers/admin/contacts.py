from telebot import types
from data.db import get_open_contacts, clear_contacts, update_contact_reply, ban_user_by_contact, is_user_banned, get_contact_by_id
from config import ADMIN_ID
from utils.security_logger import security_logger
from utils.menu import get_admin_menu, is_admin
from state.users import user_data

def register_contacts_handlers(bot, logger):
    @bot.message_handler(func=lambda m: m.text == "📨 Обращения пользователей" and is_admin(m.from_user.id))
    def handle_contacts_menu(message):
        try:
            contacts = get_open_contacts()
            if not contacts:
                bot.send_message(message.chat.id, "📭 Нет обращений, ожидающих ответа.", reply_markup=get_admin_menu())
                return
            
            # Отправляем каждое обращение отдельным сообщением с кнопками
            for contact in contacts:
                contact_id, tg_id, user_contact, contact_text, admin_reply, status, contact_time, reply_at, banned, ban_reason = contact
                
                msg = f"📨 Обращение #{contact_id}\n"
                msg += f"👤 Пользователь: {tg_id}\n"
                msg += f"📞 Контакт: {user_contact or 'не указан'}\n"
                msg += f"📅 Время: {contact_time}\n"
                msg += f"📝 Текст: {contact_text}\n"
                msg += f"📊 Статус: {status}"
                
                # Проверяем, заблокирован ли пользователь
                if is_user_banned(tg_id):
                    msg += f"\n🚫 Пользователь заблокирован"
                    if ban_reason:
                        msg += f" (причина: {ban_reason})"
                
                # Создаем кнопки только для ожидающих ответа обращений
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("💬 Ответить", callback_data=f"reply_to_contact:{contact_id}"))
                
                # Добавляем кнопку блокировки, если пользователь не заблокирован
                if not is_user_banned(tg_id):
                    markup.add(types.InlineKeyboardButton("🚫 Заблокировать пользователя", callback_data=f"ban_user:{tg_id}:{contact_id}"))
                else:
                    markup.add(types.InlineKeyboardButton("✅ Пользователь заблокирован", callback_data="user_already_banned"))
                
                bot.send_message(message.chat.id, msg, reply_markup=markup)
            
            logger.info(f"Admin {message.from_user.id} viewed open contacts")
        except Exception as e:
            logger.error(f"Error in handle_contacts_menu: {e}")

    @bot.message_handler(commands=["ClearContacts"])
    def handle_clear_contacts(message):
        if not is_admin(message.from_user.id):
            security_logger.log_failed_login(
                message.from_user.id, 
                message.from_user.username or "unknown", 
                "Unauthorized access to admin command ClearContacts"
            )
            logger.warning(f"User {message.from_user.id} tried to access admin command ClearContacts")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, очистить обращения", callback_data="confirm_clear_contacts"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_clear_contacts")
        )
        bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите удалить все обращения?\nЭто действие необратимо.", reply_markup=markup)
        logger.info(f"Admin {message.from_user.id} initiated ClearContacts")

    @bot.callback_query_handler(func=lambda c: c.data in ["confirm_clear_contacts", "cancel_clear_contacts"])
    def handle_clear_contacts_confirm(call):
        if not is_admin(call.from_user.id):
            security_logger.log_unauthorized_access(
                call.from_user.id,
                call.from_user.username or "unknown",
                "admin_contacts_clear",
                call.data
            )
            logger.warning(f"User {call.from_user.id} tried to confirm contacts clear without admin rights")
            return
        if call.data == "confirm_clear_contacts":
            try:
                clear_contacts()
                bot.edit_message_text("🧹 Обращения успешно очищены.", call.message.chat.id, call.message.message_id)
                logger.info(f"Admin {call.from_user.id} cleared contacts")
            except Exception as e:
                bot.send_message(call.message.chat.id, "❌ Ошибка при очистке обращений. Попробуйте позже.")
                logger.error(f"Error clearing contacts: {e}")
        else:
            bot.edit_message_text("❌ Очистка обращений отменена.", call.message.chat.id, call.message.message_id)
            logger.info(f"Admin {call.from_user.id} cancelled contacts clear")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("ban_user:"))
    def handle_ban_user(call):
        if not is_admin(call.from_user.id):
            security_logger.log_unauthorized_access(
                call.from_user.id,
                call.from_user.username or "unknown",
                "admin_ban_user",
                call.data
            )
            bot.answer_callback_query(call.id, "Нет прав")
            return
        
        try:
            # Парсим данные: ban_user:tg_id:contact_id
            parts = call.data.split(":")
            user_tg_id = parts[1]
            contact_id = parts[2]
            
            # Сохраняем данные для блокировки
            user_data[call.message.chat.id] = {
                "banning_user": True,
                "user_tg_id": user_tg_id,
                "contact_id": contact_id
            }
            
            msg = f"🚫 Блокировка пользователя {user_tg_id}\n\n"
            msg += "✍️ Введите причину блокировки (или нажмите '🔙 Отмена'):"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("🔙 Отмена")
            
            bot.send_message(call.message.chat.id, msg, reply_markup=markup)
            bot.register_next_step_handler(call.message, process_ban_user)
            
            logger.info(f"Admin {call.from_user.id} started banning user {user_tg_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_ban_user: {e}")

    def process_ban_user(message):
        if not is_admin(message.from_user.id):
            return
        
        chat_id = message.chat.id
        
        if chat_id not in user_data or not user_data[chat_id].get("banning_user"):
            bot.send_message(chat_id, "❌ Данные для блокировки не найдены.", reply_markup=get_admin_menu())
            return
        
        if message.text == "🔙 Отмена":
            del user_data[chat_id]
            bot.send_message(chat_id, "❌ Блокировка отменена.", reply_markup=get_admin_menu())
            return
        
        try:
            user_tg_id = user_data[chat_id]["user_tg_id"]
            contact_id = user_data[chat_id]["contact_id"]
            ban_reason = message.text
            
            # Блокируем пользователя
            ban_user_by_contact(user_tg_id, ban_reason)
            
            # Отправляем уведомление пользователю о блокировке
            try:
                notification_msg = (
                    f"🚫 <b>Вы заблокированы</b>\n\n"
                    f"Причина: {ban_reason}\n\n"
                    f"⚠️ <b>Ограничения:</b>\n"
                    f"• Вы не можете отправлять обращения администратору\n"
                    f"• Весь остальной функционал бота остается доступным\n\n"
                    f"📞 Если считаете, что блокировка произошла по ошибке, свяжитесь с администратором другим способом."
                )
                bot.send_message(user_tg_id, notification_msg, parse_mode="HTML")
                logger.info(f"Ban notification sent to user {user_tg_id}")
            except Exception as e:
                logger.error(f"Failed to send ban notification to user {user_tg_id}: {e}")
            
            # Очищаем данные
            del user_data[chat_id]
            
            bot.send_message(chat_id, f"✅ Пользователь {user_tg_id} заблокирован!\nПричина: {ban_reason}", reply_markup=get_admin_menu())
            logger.info(f"Admin {message.from_user.id} banned user {user_tg_id} with reason: {ban_reason}")
            
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при блокировке пользователя. Попробуйте позже.", reply_markup=get_admin_menu())
            logger.error(f"Error banning user: {e}")

    @bot.callback_query_handler(func=lambda c: c.data == "user_already_banned")
    def handle_user_already_banned(call):
        bot.answer_callback_query(call.id, "Пользователь уже заблокирован")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reply_to_contact:"))
    def handle_reply_to_contact(call):
        if not is_admin(call.from_user.id):
            security_logger.log_unauthorized_access(
                call.from_user.id,
                call.from_user.username or "unknown",
                "admin_contact_reply",
                call.data
            )
            bot.answer_callback_query(call.id, "Нет прав")
            return
        
        try:
            contact_id = int(call.data.split(":")[1])
            
            # Получаем информацию об обращении по ID
            contact = get_contact_by_id(contact_id)
            
            if not contact:
                bot.answer_callback_query(call.id, "Обращение не найдено")
                return
            
            contact_id, tg_id, user_contact, contact_text, admin_reply, status, contact_time, reply_at, banned, ban_reason = contact
            
            # Проверяем, что обращение еще ожидает ответа
            if status != "Ожидает ответа":
                bot.answer_callback_query(call.id, "Обращение уже обработано")
                return
            
            # Сохраняем данные для ответа
            user_data[call.message.chat.id] = {
                "replying_to_contact": True,
                "contact_id": contact_id,
                "user_tg_id": tg_id,
                "contact_text": contact_text
            }
            
            msg = f"💬 Ответ на обращение #{contact_id}\n"
            msg += f"👤 Пользователь: {tg_id}\n"
            msg += f"�� Текст обращения: {contact_text}\n\n"
            
            msg += "✍️ Введите ваш ответ или отправьте файл (фото, документ, голосовое, видео):\n\n"
            msg += "Для отмены нажмите '🔙 Отмена'"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("🔙 Отмена")
            
            bot.send_message(call.message.chat.id, msg, reply_markup=markup)
            bot.register_next_step_handler(call.message, process_contact_reply)
            
            logger.info(f"Admin {call.from_user.id} started replying to contact {contact_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_reply_to_contact: {e}")

    def process_contact_reply(message):
        if not is_admin(message.from_user.id):
            return
        
        chat_id = message.chat.id
        
        if chat_id not in user_data or not user_data[chat_id].get("replying_to_contact"):
            bot.send_message(chat_id, "❌ Данные для ответа не найдены.", reply_markup=get_admin_menu())
            return
        
        if message.text == "🔙 Отмена":
            del user_data[chat_id]
            bot.send_message(chat_id, "❌ Ответ отменен.", reply_markup=get_admin_menu())
            return
        
        try:
            contact_id = user_data[chat_id]["contact_id"]
            user_tg_id = user_data[chat_id]["user_tg_id"]
            contact_text = user_data[chat_id]["contact_text"]
            
            # Отправляем ответ пользователю
            reply_text = f"💬 Ответ на ваше обращение:\n\n{message.text}"
            bot.send_message(user_tg_id, reply_text)
            
            # Обновляем обращение в БД
            update_contact_reply(contact_id, message.text)
            
            # Очищаем данные
            del user_data[chat_id]
            
            bot.send_message(chat_id, "✅ Ответ отправлен пользователю!", reply_markup=get_admin_menu())
            logger.info(f"Admin {message.from_user.id} replied to contact {contact_id}")
            
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при отправке ответа. Попробуйте позже.", reply_markup=get_admin_menu())
            logger.error(f"Error sending contact reply: {e}")

    @bot.message_handler(content_types=['photo', 'document', 'voice', 'video', 'video_note'])
    def handle_media_contact_reply(message):
        if not is_admin(message.from_user.id):
            return
        
        chat_id = message.chat.id
        
        if chat_id not in user_data or not user_data[chat_id].get("replying_to_contact"):
            return
        
        try:
            contact_id = user_data[chat_id]["contact_id"]
            user_tg_id = user_data[chat_id]["user_tg_id"]
            contact_text = user_data[chat_id]["contact_text"]
            
            # Получаем file_id в зависимости от типа медиа
            file_id = None
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.document:
                file_id = message.document.file_id
            elif message.voice:
                file_id = message.voice.file_id
            elif message.video:
                file_id = message.video.file_id
            elif message.video_note:
                file_id = message.video_note.file_id
            
            if not file_id:
                bot.send_message(chat_id, "❌ Не удалось обработать файл.", reply_markup=get_admin_menu())
                return
            
            # Отправляем медиа пользователю
            reply_text = f"💬 Ответ на ваше обращение #{contact_id}:"
            
            try:
                if message.photo:
                    bot.send_photo(user_tg_id, file_id, caption=reply_text)
                elif message.document:
                    bot.send_document(user_tg_id, file_id, caption=reply_text)
                elif message.voice:
                    bot.send_voice(user_tg_id, file_id, caption=reply_text)
                elif message.video:
                    bot.send_video(user_tg_id, file_id, caption=reply_text)
                elif message.video_note:
                    bot.send_video_note(user_tg_id, file_id)
                    bot.send_message(user_tg_id, reply_text)
                
                # Обновляем обращение в БД
                update_contact_reply(contact_id, f"[Файл отправлен: {message.content_type}]")
                
                # Очищаем данные
                del user_data[chat_id]
                
                bot.send_message(chat_id, "✅ Файл отправлен пользователю!", reply_markup=get_admin_menu())
                logger.info(f"Admin {message.from_user.id} sent media reply to contact {contact_id}")
                
            except Exception as e:
                bot.send_message(chat_id, f"❌ Не удалось отправить файл пользователю: {str(e)}", reply_markup=get_admin_menu())
                logger.error(f"Error sending media to user: {e}")
            
        except Exception as e:
            bot.send_message(chat_id, "❌ Ошибка при отправке файла. Попробуйте позже.", reply_markup=get_admin_menu())
            logger.error(f"Error in handle_media_contact_reply: {e}") 
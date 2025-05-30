import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Telegram Bot token and Google Sheets details
TOKEN = "7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs"  # TODO: replace with your bot's token
SHEET_NAME = "Заявки на обучение"        # Google Sheet name or ID
CREDENTIALS_FILE = "creds.json"        # Path to your Google API credentials JSON

# Initialize bot and Google Sheets client
bot = telebot.TeleBot(TOKEN)
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    gs_client = gspread.authorize(creds)
    sheet = gs_client.open(SHEET_NAME).sheet1  # open the first worksheet
except Exception as e:
    print(f"Google Sheets connection error: {e}")
    sheet = None

# Dictionary to store user data during form filling
user_data = {}

def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing non-digits and handling Russian prefixes."""
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    if not digits:
        return ''
    # If starts with '8' and is 11 digits (Russian local format), replace leading '8' with '7'
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]
    return digits

def is_contact_registered(contact_value: str) -> bool:
    """Check if the given contact (username or phone) already exists in the Google Sheet."""
    if sheet is None:
        return False  # If sheet is not accessible, assume not registered (or handle accordingly)
    try:
        contacts_col = sheet.col_values(4)  # "Контакты" is the 4th column in the sheet
    except Exception as e:
        print(f"Error reading contacts column: {e}")
        return False
    # Remove header if present
    if contacts_col and "контакт" in contacts_col[0].lower():
        contacts_col = contacts_col[1:]
    contact_value = contact_value.strip()
    if contact_value == '':
        return False
    # Determine if contact_value is a username or phone number
    is_username = False
    if contact_value.startswith('@'):
        is_username = True
    if any(char.isalpha() for char in contact_value) or '_' in contact_value:
        is_username = True
    if is_username:
        # Normalize username for comparison (remove '@' and lowercase)
        username_norm = contact_value.lstrip('@').lower()
        for entry in contacts_col:
            entry_str = str(entry).strip()
            if entry_str == '':
                continue
            # Consider only entries that look like usernames (contain letters, underscores or start with '@')
            if entry_str.startswith('@') or any(char.isalpha() for char in entry_str) or '_' in entry_str:
                entry_username = entry_str.lstrip('@').lower()
                if entry_username == username_norm:
                    return True
        return False
    else:
        # Treat as phone number and normalize for comparison
        phone_norm = normalize_phone(contact_value)
        if phone_norm == '':
            return False
        for entry in contacts_col:
            entry_str = str(entry).strip()
            if entry_str == '':
                continue
            # Skip entries that look like usernames when comparing phones
            if any(char.isalpha() for char in entry_str) or '_' in entry_str or entry_str.startswith('@'):
                continue
            entry_phone = normalize_phone(entry_str)
            if entry_phone == '':
                continue
            if entry_phone == phone_norm:
                return True
        return False

# Handler for /start command
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    user = message.from_user
    contact_value = ""
    if user.username:
        # Use username as contact for checking
        contact_value = "@" + user.username
    # Note: Telegram bots cannot get a user's phone number unless the user shares it. 
    # We do not have phone here on /start, so if no username, we proceed without pre-check by phone.
    if contact_value and is_contact_registered(contact_value):
        # Contact (username) is already in the sheet, block form access
        bot.send_message(chat_id, 
                         "📝 Вы уже оставляли заявку. Мы свяжемся с вами в ближайшее время.", 
                         reply_markup=types.ReplyKeyboardRemove())
    else:
        # Not registered yet: offer the sign-up button
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        signup_btn = types.KeyboardButton("📋 Записаться")
        markup.add(signup_btn)
        bot.send_message(chat_id, 
                         "Привет! Для записи на занятие нажмите кнопку \"📋 Записаться\" и заполните анкету.", 
                         reply_markup=markup)

# Handler for pressing the "📋 Записаться" button (text match)
@bot.message_handler(func=lambda m: m.text == "📋 Записаться")
def handle_signup(message):
    chat_id = message.chat.id
    user = message.from_user
    # If user has a username, check if already registered by username
    if user.username:
        contact_value = "@" + user.username
        if is_contact_registered(contact_value):
            bot.send_message(chat_id, 
                             "📝 Вы уже оставляли заявку. Мы свяжемся с вами в ближайшее время.", 
                             reply_markup=types.ReplyKeyboardRemove())
            return
    # At this point, either user has no username or not registered yet. Start the form.
    # Initialize user data storage for this user
    user_data[user.id] = {}
    if not user.username:
        # User has no username, ask for phone contact
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        contact_btn = types.KeyboardButton("📞 Поделиться контактом", request_contact=True)
        markup.add(contact_btn)
        bot.send_message(chat_id, 
                         "Пожалуйста, отправьте номер телефона для связи. "
                         "Нажмите кнопку ниже, чтобы поделиться контактом, или введите номер вручную.", 
                         reply_markup=markup)
        # Next step: wait for contact or phone number
        bot.register_next_step_handler(message, process_contact_step)
    else:
        # User has a username and is not in sheet, use username as contact and ask for name
        user_data[user.id]['contact'] = "@" + user.username
        bot.send_message(chat_id, "Как вас зовут?")
        bot.register_next_step_handler(message, process_name_step)

# Step 1: Process contact (phone number) for users without username
def process_contact_step(message):
    chat_id = message.chat.id
    user = message.from_user
    phone = ""
    if message.content_type == 'contact' and message.contact is not None:
        # User shared contact via the button
        phone = message.contact.phone_number or ""
    elif message.text:
        # User entered phone number as text
        phone = message.text.strip()
    if phone == "":
        # No phone received, ask again
        bot.send_message(chat_id, "Не удалось получить номер телефона. Пожалуйста, отправьте номер вручную или через кнопку.")
        bot.register_next_step_handler(message, process_contact_step)
        return
    # Normalize the phone number and ensure it includes + for storage
    phone_norm = normalize_phone(phone)
    if phone_norm == "":
        bot.send_message(chat_id, "Некорректный формат номера. Попробуйте еще раз.")
        bot.register_next_step_handler(message, process_contact_step)
        return
    # Add '+' to the normalized number if not present
    contact_value = phone_norm
    if not contact_value.startswith('+'):
        contact_value = "+" + contact_value
    # Check if this phone is already registered
    if is_contact_registered(contact_value):
        bot.send_message(chat_id, 
                         "📝 Вы уже оставляли заявку. Мы свяжемся с вами в ближайшее время.", 
                         reply_markup=types.ReplyKeyboardRemove())
        return
    # Save contact and ask for name
    user_data[user.id]['contact'] = contact_value
    bot.send_message(chat_id, "Как вас зовут?")
    bot.register_next_step_handler(message, process_name_step)

# Step 2: Process name
def process_name_step(message):
    chat_id = message.chat.id
    user = message.from_user
    name = message.text.strip() if message.text else ""
    if name == "":
        bot.send_message(chat_id, "Пожалуйста, введите ваше имя.")
        bot.register_next_step_handler(message, process_name_step)
        return
    # Save name and ask for age
    user_data[user.id]['name'] = name
    bot.send_message(chat_id, "Сколько вам лет?")
    bot.register_next_step_handler(message, process_age_step)

# Step 3: Process age
def process_age_step(message):
    chat_id = message.chat.id
    user = message.from_user
    age_text = message.text.strip() if message.text else ""
    if not age_text.isdigit():
        bot.send_message(chat_id, "Пожалуйста, введите число — ваш возраст в годах.")
        bot.register_next_step_handler(message, process_age_step)
        return
    # Save age and ask for goal
    user_data[user.id]['age'] = age_text
    bot.send_message(chat_id, "Какова ваша цель обучения?")
    bot.register_next_step_handler(message, process_goal_step)

# Step 4: Process goal and save application
def process_goal_step(message):
    chat_id = message.chat.id
    user = message.from_user
    goal = message.text.strip() if message.text else ""
    if goal == "":
        # If user didn't provide a goal, use a placeholder (e.g., "-")
        goal = "-"
    # Save goal
    user_data[user.id]['goal'] = goal
    # Prepare data for Google Sheet
    contact = user_data[user.id].get('contact', '')
    name = user_data[user.id].get('name', '')
    age = user_data[user.id].get('age', '')
    goal_text = user_data[user.id].get('goal', '')
    # Append the data as a new row in the Google Sheet
    if sheet:
        try:
            sheet.append_row([name, age, goal_text, contact, ""])
        except Exception as e:
            bot.send_message(chat_id, "Ошибка сохранения заявки. Попробуйте позже.")
            print(f"Error appending to sheet: {e}")
            return  # Exit without sending success message
    # Confirm to user that the application is saved
    bot.send_message(chat_id, "✅ Ваша заявка принята! Мы свяжемся с вами в ближайшее время.", 
                     reply_markup=types.ReplyKeyboardRemove())
    # Clean up user data to finish
    user_data.pop(user.id, None)

# Start the bot
if __name__ == "__main__":
    bot.polling(none_stop=True)

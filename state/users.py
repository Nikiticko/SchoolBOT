import gspread
import os

SERVICE_ACCOUNT_FILE = "creds.json"
GOOGLE_SHEET_NAME = "Заявки на обучение"

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
sh = gc.open(GOOGLE_SHEET_NAME)
worksheet = sh.sheet1

user_data = {}
chat_contact_map = {}
used_contacts = set()
pending = {}
writing_ids = set()
   

# Загрузка уже использованных контактов
try:
    contacts_col = worksheet.col_values(5)  # "Контакты" — колонка E
    if contacts_col and contacts_col[0].strip().lower() in ["contact", "контакты"]:
        contacts_col = contacts_col[1:]
    for contact in contacts_col:
        contact = contact.strip()
        if contact:
            used_contacts.add(contact)  
except Exception as e:
    print("Error loading contacts from sheet:", e)

def get_user_status(chat_id):
    """По chat_id возвращает статус пользователя"""
    try:
        cell = worksheet.find(str(chat_id))   
        row = worksheet.row_values(cell.row)
        course = row[5] if len(row) > 5 else ""
        date = row[6] if len(row) > 6 else ""
        link = row[7] if len(row) > 7 else ""
        if not date.strip() and not link.strip():
            return True, None, None, None
        return True, date.strip(), course.strip(), link.strip()
    except:
        return False, None, None, None

def get_user_status_by_contact(contact):
    """По контактным данным (username или телефон) возвращает статус пользователя"""
    try:
        cell = worksheet.find(contact)
        row = worksheet.row_values(cell.row)
        course = row[5] if len(row) > 5 else ""
        date = row[6] if len(row) > 6 else ""
        link = row[7] if len(row) > 7 else ""
        if not date.strip() and not link.strip():
            return True, None, None, None
        return True, date.strip(), course.strip(), link.strip()
    except:
        return False, None, None, None

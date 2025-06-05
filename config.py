import os

API_TOKEN = "7906419182:AAFkvUNgQpbgAka959-gC1oL0WGvq58SPJs"
GOOGLE_SHEET_NAME = "Заявки на обучение"
SERVICE_ACCOUNT_FILE = "creds.json"

if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"Файл {SERVICE_ACCOUNT_FILE} не найден.")

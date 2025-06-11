import gspread
from google.oauth2.service_account import Credentials
from config import SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_NAME

def init_sheets():
    """Инициализация подключения к Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, 
            scopes=scope
        )
        
        client = gspread.authorize(creds)
        worksheet = client.open(GOOGLE_SHEET_NAME).sheet1
        return worksheet
    except Exception as e:
        print(f"Ошибка при инициализации Google Sheets: {str(e)}")
        raise

# Инициализируем worksheet при импорте модуля
worksheet = init_sheets() 
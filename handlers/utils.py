import re

def normalize_phone(phone):
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('8'):
        phone = '7' + phone[1:]
    return f"+{phone}"

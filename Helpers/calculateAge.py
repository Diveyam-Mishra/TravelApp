from datetime import datetime

def calculate_age(dob: datetime.date) -> int:
    today = datetime.today().date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age
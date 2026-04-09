from datetime import datetime

def format_expiry_date(date_input):
    if isinstance(date_input, datetime):
        return date_input.strftime("%d.%m.%Y")
    elif isinstance(date_input, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                date_obj = datetime.strptime(date_input, fmt)
                return date_obj.strftime("%d.%m.%Y")
            except ValueError:
                continue
        return date_input
    else:
        return str(date_input)

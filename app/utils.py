from decimal import Decimal
from passlib.context import CryptContext
import re
from datetime import datetime

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def div_ceil(nominator, denominator):
    a = nominator // denominator
    b = 1 if nominator % denominator > 0 else 0
    return a + b

def to_decimal(s):
    try:
        result = Decimal(s)
        return result
    except:
        return False

def remove_exponent(num):
    s = str(num)
    if 'E' not in s:
        return num

    l = s.split('E')
    return float(l[0]) * pow(10, int(l[1]))

def display_decimal(num):
    return remove_exponent(Decimal(num).quantize(Decimal('10') ** -3))

def is_valid_date(date_str):#, format):
    try:
        obj = datetime.strptime(date_str, "%d/%m/%Y")
        return obj.isoformat() 
    except Exception as e:
        return None

def is_positive_int(field):
    try:
        field = field.replace(" ", "")
        res = int(field)
        return res if res >= 0 else None
    except:
        return None

def is_positive_decimal(field):
    try:
        field = field.replace(" ", "")
        field = field.replace(',', '.')
        res = Decimal(field)
        return res if res >= 0 else None
    except:
        return None

def is_regex_matched(regex, field):
    return field if re.match(regex, field) else None

def is_valid_bool(field):
    values = {
        "oui": True,
        "non": False,
    }

    field = field.lower()
    if field in values.keys():
        return values[field]

    return None

def serialize_datetime(obj):
    if isinstance(obj, datetime): 
        return obj.isoformat()
    raise TypeError("Type not serializable")

def isEmptyLine(vals: list):
    isEmpty = True
    for val in vals:
        if not isEmpty:
            break

        if type(val) == str:
            val = val.strip()
            if val != '':
                isEmpty = False
        elif type(val) == list:
            isEmpty = isEmpty and isEmptyLine(val)
        else:
            raise Exception(f"Invalide value = {val} of type {type(val)}")

    return isEmpty

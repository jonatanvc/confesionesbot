import os
from dotenv import load_dotenv

load_dotenv()

def get_env_int(key: str, default: int = 0) -> int:
    val = os.getenv(key)
    if val is None or not str(val).strip():
        return default
    try:
        return int(str(val).strip())
    except ValueError:
        return default

def get_env_channel(key: str, default: str = ""):
    val = os.getenv(key)
    if val is None or not str(val).strip():
        return default
    val = str(val).strip()
    if (val.startswith("-") and val[1:].isdigit()) or val.isdigit():
        return int(val)
    return val

# Tokens y Configuración de Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "8464884387:AAFo62Jcy0zjwkF1ghG4SjngBFLDd4uJiHE").strip()
CANAL_ID = get_env_channel("CANAL_ID", "@ConfesionesUniversitarias")
GRUPO_ADMIN_ID = get_env_int("GRUPO_ADMIN_ID", -1003273428346)
CANAL_OBLIGATORIO = os.getenv("CANAL_OBLIGATORIO", "@ConfesionesUniversitarias").strip()
CANAL_OPCIONAL = os.getenv("CANAL_OPCIONAL", "@ConfesionesUniversitarias").strip()
OWNER_ID = get_env_int("OWNER_ID", 923639754)

# Configuración de Base de Datos
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()
    if not DATABASE_URL:
        DATABASE_URL = None

USE_POSTGRES = DATABASE_URL is not None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DB_DIR, 'confesiones.db')

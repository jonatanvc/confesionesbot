import telebot
from telebot import types
import os
import threading
import time
import sys
import logging
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as _TelebotInlineKeyboardButton
from datetime import datetime
from config import BOT_TOKEN, CANAL_ID, GRUPO_ADMIN_ID, CANAL_OBLIGATORIO, OWNER_ID
from database import *
from emojis import EMOJI_MAP, parse_emojis, p

if 'TERM' not in os.environ:
    os.environ['TERM'] = 'xterm'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def InlineKeyboardButton(text: str, *args, **kwargs):
    """
    Construye InlineKeyboardButton inyectando icon_custom_emoji_id cuando coincide
    con el catálogo de Emojis Animados Premium de Telegram, y remueve el emoji unicode
    del texto para evitar que aparezcan 2 emojis duplicados en el botón.
    """
    text_str = str(text).strip()
    icon_id = None

    # 1. Buscar si comienza con algún emoji del catálogo
    for emoji_char, emoji_id in sorted(EMOJI_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if text_str.startswith(emoji_char):
            icon_id = emoji_id
            text_str = text_str[len(emoji_char):].strip()
            text_str = text_str.lstrip(" \ufe0f")
            break

    # 2. Si no empieza con emoji, buscar si contiene un emoji en el texto
    if not icon_id:
        for emoji_char, emoji_id in sorted(EMOJI_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if emoji_char in text_str:
                icon_id = emoji_id
                text_str = text_str.replace(emoji_char, "").strip()
                break

    if icon_id:
        btn = _TelebotInlineKeyboardButton(text=text_str if text_str else text, *args, **kwargs)
        btn.icon_custom_emoji_id = str(icon_id)
        return btn
    else:
        return _TelebotInlineKeyboardButton(text=text, *args, **kwargs)

def escape_html(text):
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

user_drafts = {}
user_page_stack = {}
user_main_messages = {}
user_states = {}
user_states_timestamp = {}
notification_messages = {}
user_last_confession_time = {}

STATE_TIMEOUT_MINUTES = 10
COOLDOWN_CONFESION_SEGUNDOS = 300  # 5 minutos de Anti-Spam por usuario

BOT_VERSION = "3.2.0"
BOT_START_TIME = datetime.now()

MOTIVOS_RECHAZO = {
    "ofensivo": "Lenguaje ofensivo, insultos o falta de respeto hacia otros.",
    "doxxing": "Información privada, números telefónicos o datos sensibles (Doxxing).",
    "spam": "Publicidad, spam comercial o enlaces no autorizados.",
    "repetido": "Confesión repetida, vacía o sin contenido de valor.",
    "reglas": "Incumplimiento de las reglas comunitarias del canal.",
    "directo": "No cumple con las pautas de publicación del canal."
}

def set_main_message(user_id, message_id):
    user_main_messages[user_id] = message_id

def get_main_message(user_id):
    return user_main_messages.get(user_id)

def editar_mensaje_principal(chat_id, user_id, text, reply_markup=None, parse_mode="HTML"):
    parsed_text = p(text)
    message_id = get_main_message(user_id)

    if message_id:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=parsed_text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "message is not modified" in error_str:
                return True
            try:
                msg = bot.send_message(chat_id, parsed_text, reply_markup=reply_markup, parse_mode=parse_mode)
                set_main_message(user_id, msg.message_id)
                return True
            except Exception as send_error:
                logger.error(f"Error enviando mensaje para user {user_id}: {send_error}")
                return False
    else:
        try:
            msg = bot.send_message(chat_id, parsed_text, reply_markup=reply_markup, parse_mode=parse_mode)
            set_main_message(user_id, msg.message_id)
            return True
        except Exception as send_error:
            logger.error(f"Error enviando mensaje inicial para user {user_id}: {send_error}")
            return False

# Inicializar Base de Datos
init_db()

try:
    eliminadas = limpiar_confesiones_antiguas(30)
    logger.info(f"🧹 Limpieza automática: {eliminadas} confesiones de más de 30 días eliminadas")
except Exception as e:
    logger.warning(f"Error en limpieza automática: {e}")

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    disable_notification=False,
    skip_pending=True
)

def set_user_state(user_id, state):
    user_states[user_id] = state
    user_states_timestamp[user_id] = time.time()

def get_user_state(user_id):
    if user_id not in user_states:
        return None
    if user_id in user_states_timestamp:
        elapsed = time.time() - user_states_timestamp[user_id]
        if elapsed > STATE_TIMEOUT_MINUTES * 60:
            clear_user_state(user_id)
            return None
    return user_states.get(user_id)

def clear_user_state(user_id):
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_states_timestamp:
        del user_states_timestamp[user_id]

def obtener_cooldown_restante(user_id: int) -> int:
    """Devuelve segundos restantes para que el usuario pueda volver a confesar"""
    if user_id == OWNER_ID:
        return 0
    ultimo = user_last_confession_time.get(user_id)
    if not ultimo:
        return 0
    transcurrido = time.time() - ultimo
    if transcurrido < COOLDOWN_CONFESION_SEGUNDOS:
        return int(COOLDOWN_CONFESION_SEGUNDOS - transcurrido)
    return 0

def registrar_tiempo_confesion(user_id: int):
    user_last_confession_time[user_id] = time.time()

def obtener_nombre_usuario(user):
    if user.first_name:
        return escape_html(user.first_name)
    elif user.username:
        return escape_html(user.username)
    return "Amigo"

def verificar_usuario_baneado(user_id):
    if user_id == OWNER_ID:
        return False
    return usuario_esta_baneado(user_id)

def enviar_mensaje_baneo(chat_id, user_id):
    razon = obtener_razon_ban(user_id)
    mensaje = (
        "🚫 <b>Acceso Denegado</b>\n\n"
        "Estás baneado del bot de confesiones.\n\n"
        f"📋 <b>Razón:</b> {escape_html(razon) if razon else 'Incumplimiento de normas'}\n\n"
        "💬 Si consideras que es un error, puedes usar el comando /appeal."
    )
    try:
        editar_mensaje_principal(chat_id, user_id, mensaje)
    except Exception:
        pass

def verificar_baneo_handler(func):
    """Decorador para verificar baneo antes de ejecutar handlers"""
    def wrapper(message_or_call):
        user_id = message_or_call.from_user.id
        if user_id == OWNER_ID:
            return func(message_or_call)
        if verificar_usuario_baneado(user_id):
            if hasattr(message_or_call, 'message') and message_or_call.message:
                chat_id = message_or_call.message.chat.id
            elif hasattr(message_or_call, 'chat') and message_or_call.chat:
                chat_id = message_or_call.chat.id
            else:
                chat_id = user_id
            enviar_mensaje_baneo(chat_id, user_id)
            return
        return func(message_or_call)
    return wrapper

def calcular_badges(user_id):
    badges = []
    conf = obtener_confesiones_usuario(user_id)
    aceptadas = sum(1 for c in conf if c['estado'] == 'aceptada')
    if aceptadas >= 1:
        badges.append("👤 Usuario Activo")
    if aceptadas >= 5:
        badges.append("🌟 Confesionador Legendario")
    return badges

def markup_volver_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏠 Volver al menú", callback_data="volver_menu"))
    return markup

def markup_back():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("◀️ Atrás", callback_data="volver_atras"))
    return markup

def push_page(user_id, page_id, data=None):
    stack = user_page_stack.get(user_id, [])
    stack.append((page_id, data))
    user_page_stack[user_id] = stack

def pop_page(user_id):
    stack = user_page_stack.get(user_id, [])
    if not stack:
        return None
    stack.pop()
    if not stack:
        return None
    return stack.pop()

def peek_current(user_id):
    stack = user_page_stack.get(user_id, [])
    return stack[-1] if stack else None

def safe_answer_callback(call_id, text=None, show_alert=False):
    try:
        bot.answer_callback_query(call_id, text, show_alert=show_alert)
        return True
    except Exception:
        return False

def registrar_notificacion_pendiente(user_id, chat_id, message_id):
    if user_id in notification_messages:
        old_chat_id, old_message_id = notification_messages[user_id]
        try:
            bot.delete_message(old_chat_id, old_message_id)
        except Exception:
            pass
    notification_messages[user_id] = (chat_id, message_id)

def eliminar_notificacion_pendiente(user_id):
    if user_id in notification_messages:
        try:
            chat_id, message_id = notification_messages[user_id]
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        finally:
            notification_messages.pop(user_id, None)

def usuario_unido(user_id):
    if not CANAL_OBLIGATORIO:
        return True
    try:
        member = bot.get_chat_member(CANAL_OBLIGATORIO, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

def is_admin(user_id):
    try:
        if user_id == OWNER_ID:
            return True
        if not GRUPO_ADMIN_ID:
            return False
        member = bot.get_chat_member(GRUPO_ADMIN_ID, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

def requerir_membresia(message_or_call):
    user = message_or_call.from_user
    user_id = user.id
    chat_id = message_or_call.chat.id if hasattr(message_or_call, 'chat') else (message_or_call.message.chat.id if hasattr(message_or_call, 'message') else user_id)

    if user_id == OWNER_ID or not CANAL_OBLIGATORIO:
        return True

    if not usuario_unido(user_id):
        markup = InlineKeyboardMarkup()
        canal_str = str(CANAL_OBLIGATORIO).strip()
        if canal_str.startswith("http"):
            canal_url = canal_str
        elif canal_str.startswith("@"):
            canal_url = f"https://t.me/{canal_str.lstrip('@')}"
        elif not canal_str.startswith("-"):
            canal_url = f"https://t.me/{canal_str}"
        else:
            canal_url = f"https://t.me/{str(CANAL_ID).lstrip('@')}" if str(CANAL_ID).startswith('@') else None

        if canal_url:
            markup.add(InlineKeyboardButton("📢 Unirme al canal", url=canal_url))
        markup.add(InlineKeyboardButton("🔄 Ya me uní (Verificar)", callback_data="verificar_suscripcion"))

        editar_mensaje_principal(
            chat_id,
            user_id,
            "🚫 <b>¡Necesitas unirte a nuestro canal!</b>\n\n📌 Para poder interactuar con el bot debes estar suscrito al canal oficial.\n\nPresiona <b>Unirme al canal</b> y luego pulsa en <b>Ya me uní (Verificar)</b>.",
            reply_markup=markup
        )
        return False
    return True

def markup_start(user_is_admin=False):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💬 Confesiones", callback_data="menu_confesiones"))
    if user_is_admin:
        markup.add(InlineKeyboardButton("🛠️ Panel Admin", callback_data="panel_admin"))
    return markup

def markup_confesiones():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✍️ Hacer Confesión", callback_data="enviar_confesion"))
    markup.add(InlineKeyboardButton("📂 Mis Confesiones", callback_data="ver_confesiones"))
    markup.add(InlineKeyboardButton("📊 Mis Estadísticas", callback_data="mis_estadisticas"))
    markup.add(InlineKeyboardButton("📋 Reglas del Bot", callback_data="ver_reglas"))
    markup.add(InlineKeyboardButton("❓ Ayuda/FAQ", callback_data="ayuda"))
    markup.add(InlineKeyboardButton("◀️ Volver al Menú", callback_data="volver_menu"))
    return markup

def markup_admin_moderacion(conf_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Aceptar", callback_data=f"aceptar_{conf_id}"),
        InlineKeyboardButton("❌ Rechazar", callback_data=f"menu_rechazo_{conf_id}")
    )
    markup.add(
        InlineKeyboardButton("⚠️ Advertir Autor", callback_data=f"qwarn_{conf_id}"),
        InlineKeyboardButton("🚫 Banear Autor", callback_data=f"qban_{conf_id}")
    )
    return markup

def markup_menu_rechazo(conf_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🚫 Lenguaje Ofensivo / Insultos", callback_data=f"motivo_{conf_id}_ofensivo"),
        InlineKeyboardButton("🔏 Doxxing / Datos Personales", callback_data=f"motivo_{conf_id}_doxxing"),
        InlineKeyboardButton("📢 Spam / Publicidad", callback_data=f"motivo_{conf_id}_spam"),
        InlineKeyboardButton("🔄 Repetido o Vacío", callback_data=f"motivo_{conf_id}_repetido"),
        InlineKeyboardButton("⚖️ Incumple Reglas Generales", callback_data=f"motivo_{conf_id}_reglas"),
        InlineKeyboardButton("❌ Rechazo Directo (Sin motivo)", callback_data=f"motivo_{conf_id}_directo"),
        InlineKeyboardButton("◀️ Volver a Moderación", callback_data=f"mod_volver_{conf_id}")
    )
    return markup

def show_menu_page(chat_id, page_id, user, call=None):
    uid = user.id

    if page_id == 'enviar_confesion':
        restante = obtener_cooldown_restante(uid)
        if restante > 0:
            minutos = restante // 60
            segundos = restante % 60
            tiempo_str = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
            text = (
                "⏳ <b>Modo Anti-Spam Activado</b>\n\n"
                f"Debes esperar <b>{tiempo_str}</b> antes de poder enviar otra confesión.\n\n"
                "💡 <i>Límite: 1 confesión cada 5 minutos por usuario para garantizar la calidad del canal.</i>"
            )
            editar_mensaje_principal(chat_id, uid, text, reply_markup=markup_back())
            return

        text = (
            "📖 Lee las reglas antes de confesar.\n\n"
            "✍️ Envía tu confesión (texto, foto o encuesta)\n\n"
            "Te mostraremos una vista previa para confirmar."
        )
        editar_mensaje_principal(chat_id, uid, text, reply_markup=markup_back())
        set_user_state(uid, 'awaiting_confession')

    elif page_id == 'ver_confesiones':
        confesiones = obtener_confesiones_usuario(uid)
        if not confesiones:
            texto = "📭 ¡Aún no tienes confesiones registradas!"
            editar_mensaje_principal(chat_id, uid, texto, reply_markup=markup_back())
            return

        texto = "📂 <b>Tus Confesiones</b>\n\n"
        for c in confesiones:
            safe_conf = escape_html(c['confesion'][:50] + "..." if len(c['confesion']) > 50 else c['confesion'])
            estado_emoji = {'pendiente': '⏳', 'aceptada': '✅', 'rechazada': '❌'}.get(c['estado'], '❓')
            tipo_icon = '💬' if (c.get('tipo') or 'text') == 'text' else ('📷' if c.get('tipo') == 'photo' else ('📊' if c.get('tipo') == 'poll' else '📦'))
            texto += f"{estado_emoji} <b>No. {c['id']}</b> ({c['estado'].capitalize()}) {tipo_icon}\n🕒 {c['fecha']}\n💬 <i>{safe_conf}</i>\n\n"

        editar_mensaje_principal(chat_id, uid, texto, reply_markup=markup_back())

    elif page_id == 'mis_estadisticas':
        stats = contar_confesiones_usuario(uid)
        badges = calcular_badges(uid)
        nombre = obtener_nombre_usuario(user)
        texto = f"📊 <b>Tus Estadísticas, {nombre}</b>\n\n📈 Resumen:\n📌 Total: {stats['total']}\n✅ Aceptadas: {stats['aceptadas']}\n⏳ Pendientes: {stats['pendientes']}\n❌ Rechazadas: {stats['rechazadas']}\n"
        if badges:
            texto += "\n🏆 Tus Badges:\n"
            for badge in badges:
                texto += f"⤏ {badge}\n"
        else:
            texto += "\n💡 ¡Comparte más confesiones para ganar insignias!"

        editar_mensaje_principal(chat_id, uid, texto, reply_markup=markup_back())

    elif page_id == 'ayuda':
        text = "❓ <b>Preguntas Frecuentes</b>\n\n✍️ ¿Cómo envío una confesión?\nMenú → '✍️ Enviar' → Escribe → Confirma\n\n🔒 ¿Son anónimas?\nSí, se publican sin tu nombre ni usuario.\n\n⏱️ ¿Cuánto tarda la revisión?\nGeneralmente de 1 a 24 horas.\n\n❌ ¿Y si es rechazada?\nRecibirás el motivo específico del moderador."
        editar_mensaje_principal(chat_id, uid, text, reply_markup=markup_back())

    elif page_id == 'ver_reglas':
        text = (
            "📋 <b>Reglas del Bot</b>\n\n"
            "<b>❌ PROHIBIDO:</b>\n"
            "• 🚫 <b>Ofender</b>, insultar o acosar\n"
            "• 🔏 <b>Doxxing</b> (datos privados o números)\n"
            "• 📢 <b>Spam</b>, publicidad o enlaces no autorizados\n"
            "• 👤 <b>Suplantación</b> de identidad\n"
            "• ⛔ <b>Contenido explícito</b> o ilegal\n\n"
            "<b>✅ PERMITIDO:</b>\n"
            "• 💭 Confesiones y desahogos sinceros\n"
            "• 💬 Compartir anécdotas y experiencias\n"
            "• 💡 Pedir consejos respetuosos a la comunidad\n\n"
            "<b>🚨 Sistema de Advertencias:</b>\n"
            "• ⚠️ <b>1ª Advertencia:</b> Aviso preventivo\n"
            "• ⚠️ <b>2ª Advertencia:</b> Último aviso\n"
            "• 🚫 <b>3ª Advertencia:</b> BAN DEFINITIVO"
        )
        editar_mensaje_principal(chat_id, uid, text, reply_markup=markup_back())

@bot.message_handler(commands=["start"])
@verificar_baneo_handler
def cmd_start(message):
    user_id = message.from_user.id
    registrar_usuario(user_id, message.from_user.username or "SinUsername")
    eliminar_notificacion_pendiente(user_id)

    # Intentar borrar el mensaje /start del usuario para mantener el chat limpio
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    if not requerir_membresia(message):
        return

    nombre = obtener_nombre_usuario(message.from_user)
    user_is_admin = is_admin(message.from_user.id)

    texto_bienvenida = (
        f"👋 ¡Hola, {nombre}!\n\n"
        "💭 <b>Confesiones Anónimas</b>\n"
        "Envía confesiones al canal de forma 100% anónima.\n\n"
        "🚀 Usa los botones interactivos para comenzar."
    )
    editar_mensaje_principal(
        message.chat.id,
        user_id,
        texto_bienvenida,
        reply_markup=markup_start(user_is_admin)
    )

@bot.callback_query_handler(func=lambda c: c.data == "verificar_suscripcion")
@verificar_baneo_handler
def callback_verificar_suscripcion(call):
    user_id = call.from_user.id
    if usuario_unido(user_id):
        safe_answer_callback(call.id, "✅ ¡Verificación exitosa! Bienvenido/a.")
        user_is_admin = is_admin(user_id)
        nombre = obtener_nombre_usuario(call.from_user)
        texto_bienvenida = (
            f"👋 ¡Hola, {nombre}!\n\n"
            "💭 <b>Confesiones Anónimas</b>\n"
            "Envía confesiones al canal de forma 100% anónima.\n\n"
            "🚀 Usa los botones interactivos para comenzar."
        )
        editar_mensaje_principal(
            call.message.chat.id,
            user_id,
            texto_bienvenida,
            reply_markup=markup_start(user_is_admin)
        )
    else:
        safe_answer_callback(call.id, "❌ Aún no te has unido al canal. Únete para continuar.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "panel_admin")
def panel_admin_callback(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        safe_answer_callback(call.id, "⛔ No tienes permisos de administrador.")
        return

    eliminar_notificacion_pendiente(user_id)
    push_page(user_id, 'menu')
    push_page(user_id, 'panel_admin')

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 Estadísticas avanzadas", callback_data="estadisticas_avanzadas"))
    markup.add(InlineKeyboardButton("🧾 Sistema de appeals", callback_data="sistema_appeals"))
    markup.add(InlineKeyboardButton("📈 Reporte general", callback_data="reportes_automaticos"))
    markup.add(InlineKeyboardButton("◀️ Atrás", callback_data="volver_atras"))
    markup.add(InlineKeyboardButton("🏠 Volver al menú", callback_data="volver_menu"))

    editar_mensaje_principal(
        call.message.chat.id,
        user_id,
        "🛠️ <b>Panel de Administración</b>\n\nSeleccione una opción:",
        reply_markup=markup
    )
    safe_answer_callback(call.id, "🛠️ Panel de administración")

@bot.callback_query_handler(func=lambda c: c.data == "menu_confesiones")
@verificar_baneo_handler
def menu_confesiones_callback(call):
    user_id = call.from_user.id
    registrar_usuario(user_id, call.from_user.username or "SinUsername")
    eliminar_notificacion_pendiente(user_id)

    if not requerir_membresia(call):
        safe_answer_callback(call.id)
        return

    push_page(call.from_user.id, 'menu')
    push_page(call.from_user.id, 'menu_confesiones')

    texto = (
        "🗂️ <b>Panel de Confesiones</b>\n\n"
        "Selecciona una opción para gestionar tus confesiones:\n\n"
        "✍️ <b>Hacer Confesión:</b> Envía una nueva confesión anónima\n"
        "📂 <b>Mis Confesiones:</b> Revisa el estado de tus envíos\n"
        "📊 <b>Estadísticas:</b> Mira tu actividad\n"
        "📋 <b>Reglas:</b> Normas del bot\n"
        "❓ <b>Ayuda:</b> Preguntas frecuentes"
    )
    editar_mensaje_principal(call.message.chat.id, user_id, texto, reply_markup=markup_confesiones())
    safe_answer_callback(call.id, "🗂️ Panel de confesiones")

@bot.callback_query_handler(func=lambda c: c.data in ("enviar_confesion", "ver_confesiones", "ayuda", "mis_estadisticas", "ver_reglas"))
@verificar_baneo_handler
def menu_callback(call):
    user_id = call.from_user.id
    registrar_usuario(user_id, call.from_user.username or "SinUsername")
    eliminar_notificacion_pendiente(user_id)

    if not requerir_membresia(call):
        safe_answer_callback(call.id)
        return

    current = peek_current(call.from_user.id)
    if current and current[0] != call.data:
        push_page(call.from_user.id, current[0] if current else 'menu')
    push_page(call.from_user.id, call.data)

    show_menu_page(call.message.chat.id, call.data, call.from_user, call=call)
    safe_answer_callback(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "volver_atras")
@verificar_baneo_handler
def volver_atras_callback(call):
    user_id = call.from_user.id
    eliminar_notificacion_pendiente(user_id)
    clear_user_state(user_id)

    prev = pop_page(user_id)
    if not prev:
        user_is_admin = is_admin(user_id)
        editar_mensaje_principal(call.message.chat.id, user_id, "🏠 Menú principal", reply_markup=markup_start(user_is_admin))
        safe_answer_callback(call.id, "🏠 Volviendo al menú")
        return

    page_id, data = prev
    if page_id == 'menu':
        user_is_admin = is_admin(user_id)
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, "🏠 Menú principal", reply_markup=markup_start(user_is_admin))
        safe_answer_callback(call.id, "🏠 Volviendo al menú")
        return

    if page_id == 'panel_admin':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 Estadísticas avanzadas", callback_data="estadisticas_avanzadas"))
        markup.add(InlineKeyboardButton("🧾 Sistema de appeals", callback_data="sistema_appeals"))
        markup.add(InlineKeyboardButton("📈 Reporte general", callback_data="reportes_automaticos"))
        markup.add(InlineKeyboardButton("◀️ Atrás", callback_data="volver_atras"))
        markup.add(InlineKeyboardButton("🏠 Volver al menú", callback_data="volver_menu"))
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, "🛠️ <b>Panel de Administración</b>\n\nSeleccione una opción:", reply_markup=markup)
        safe_answer_callback(call.id, "🛠️ Panel de administración")
        return

    if page_id == 'menu_confesiones':
        texto = (
            "🗂️ <b>Panel de Confesiones</b>\n\n"
            "Selecciona una opción para gestionar tus confesiones:\n\n"
            "✍️ <b>Hacer Confesión:</b> Envía una nueva confesión anónima\n"
            "📂 <b>Mis Confesiones:</b> Revisa el estado de tus envíos\n"
            "📊 <b>Estadísticas:</b> Mira tu actividad\n"
            "📋 <b>Reglas:</b> Normas del bot"
        )
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, texto, reply_markup=markup_confesiones())
        safe_answer_callback(call.id, "🗂️ Panel de confesiones")
        return

    if page_id in ('enviar_confesion', 'ver_confesiones', 'mis_estadisticas', 'ayuda', 'ver_reglas'):
        show_menu_page(call.message.chat.id, page_id, call.from_user, call=call)
        safe_answer_callback(call.id)
        return

    user_is_admin = is_admin(call.from_user.id)
    editar_mensaje_principal(call.message.chat.id, call.from_user.id, "🏠 Menú principal", reply_markup=markup_start(user_is_admin))
    safe_answer_callback(call.id, "🏠 Volviendo al menú")

@bot.message_handler(func=lambda m: get_user_state(m.from_user.id) == 'awaiting_confession', content_types=['text'])
@verificar_baneo_handler
def recibir_confesion(message):
    user_id = message.from_user.id
    eliminar_notificacion_pendiente(user_id)

    # Intentar limpiar el texto del usuario para mantener el chat limpio
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    if not requerir_membresia(message):
        return

    restante = obtener_cooldown_restante(user_id)
    if restante > 0:
        minutos = restante // 60
        segundos = restante % 60
        tiempo_str = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
        editar_mensaje_principal(
            message.chat.id,
            user_id,
            f"⏳ <b>Anti-Spam:</b> Debes esperar <b>{tiempo_str}</b> antes de enviar otra confesión.",
            reply_markup=markup_back()
        )
        return

    registrar_usuario(user_id, message.from_user.username or "SinUsername")
    texto = (message.text or "").strip()
    if not texto:
        editar_mensaje_principal(message.chat.id, user_id, "⚠️ <i>¡Mensaje vacío! Envía tu confesión de nuevo. 💭</i>", reply_markup=markup_back())
        return
    if len(texto) > 1000:
        editar_mensaje_principal(message.chat.id, user_id, f"📏 ¡Confesión muy larga! Máximo 1000 caracteres (escribiste {len(texto)}).", reply_markup=markup_back())
        return

    user_drafts[user_id] = {
        'tipo': 'text',
        'texto': texto,
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': user_id,
        'username': message.from_user.username or "SinUsername"
    }
    safe_text = escape_html(texto)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Enviar", callback_data="confirmar_envio"),
        InlineKeyboardButton("✏️ Editar", callback_data="editar_confesion"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_confesion")
    )
    editar_mensaje_principal(message.chat.id, user_id, f"👀 <b>Vista Previa de tu Confesión</b>\n\n💬 <code>{safe_text}</code>", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_state(m.from_user.id) == 'awaiting_confession', content_types=['photo'])
@verificar_baneo_handler
def recibir_confesion_foto(message):
    user_id = message.from_user.id
    eliminar_notificacion_pendiente(user_id)

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    if not requerir_membresia(message):
        return

    restante = obtener_cooldown_restante(user_id)
    if restante > 0:
        minutos = restante // 60
        segundos = restante % 60
        tiempo_str = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
        editar_mensaje_principal(message.chat.id, user_id, f"⏳ <b>Anti-Spam:</b> Espera <b>{tiempo_str}</b> antes de enviar otra confesión.", reply_markup=markup_back())
        return

    registrar_usuario(user_id, message.from_user.username or "SinUsername")
    if not message.photo:
        editar_mensaje_principal(message.chat.id, user_id, "⚠️ No se recibió la foto. Intenta nuevamente.", reply_markup=markup_back())
        return

    file_id = message.photo[-1].file_id
    caption = (message.caption or "").strip()
    if len(caption) > 1000:
        editar_mensaje_principal(message.chat.id, user_id, f"📏 Pie de foto muy largo (máx 1000). Escribiste: {len(caption)}.", reply_markup=markup_back())
        return

    user_drafts[user_id] = {
        'tipo': 'photo',
        'file_id': file_id,
        'texto': caption,
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': user_id,
        'username': message.from_user.username or "SinUsername"
    }
    safe_caption = escape_html(caption)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Enviar", callback_data="confirmar_envio"),
        InlineKeyboardButton("✏️ Editar", callback_data="editar_confesion"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_confesion")
    )
    preview_text = f"👀 <b>Vista Previa de tu Confesión</b>\n\n📷 Foto recibida.\n💬 Caption: <code>{safe_caption}</code>"
    editar_mensaje_principal(message.chat.id, user_id, preview_text, reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_state(m.from_user.id) == 'awaiting_confession', content_types=['poll'])
@verificar_baneo_handler
def recibir_confesion_encuesta(message):
    user_id = message.from_user.id
    eliminar_notificacion_pendiente(user_id)

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    if not requerir_membresia(message):
        return

    restante = obtener_cooldown_restante(user_id)
    if restante > 0:
        minutos = restante // 60
        segundos = restante % 60
        tiempo_str = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
        editar_mensaje_principal(message.chat.id, user_id, f"⏳ <b>Anti-Spam:</b> Espera <b>{tiempo_str}</b> antes de enviar otra confesión.", reply_markup=markup_back())
        return

    poll = message.poll
    if not poll:
        editar_mensaje_principal(message.chat.id, user_id, "⚠️ No se recibió la encuesta.", reply_markup=markup_back())
        return
    question = (poll.question or "").strip()
    options = [opt.text for opt in (poll.options or [])]
    multiple = bool(getattr(poll, 'allows_multiple_answers', False))

    if not question or len(question) > 255:
        editar_mensaje_principal(message.chat.id, user_id, "⚠️ Pregunta inválida o muy larga (máx 255).", reply_markup=markup_back())
        return
    if not options or len(options) < 2:
        editar_mensaje_principal(message.chat.id, user_id, "⚠️ La encuesta necesita al menos 2 opciones.", reply_markup=markup_back())
        return

    user_drafts[user_id] = {
        'tipo': 'poll',
        'question': question,
        'options': options,
        'multiple': multiple,
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': user_id,
        'username': message.from_user.username or "SinUsername"
    }
    safe_q = escape_html(question)
    opciones_txt = "\n".join([f"• {escape_html(o)}" for o in options])
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Enviar", callback_data="confirmar_envio"),
        InlineKeyboardButton("✏️ Editar", callback_data="editar_confesion"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_confesion")
    )
    preview_text = (
        "👀 <b>Vista Previa de tu Encuesta</b>\n\n"
        f"📊 Pregunta: <code>{safe_q}</code>\n"
        f"🔢 Opciones:\n{opciones_txt}\n"
        f"🔁 Múltiples respuestas: {'Sí' if multiple else 'No'}"
    )
    editar_mensaje_principal(message.chat.id, user_id, preview_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "confirmar_envio")
@verificar_baneo_handler
def confirmar_envio(call):
    user_id = call.from_user.id
    if user_id not in user_drafts:
        safe_answer_callback(call.id, "⚠️ No hay borrador disponible")
        return

    draft = user_drafts[user_id]
    tipo = draft.get('tipo', 'text')

    if tipo == 'text':
        conf_id = guardar_confesion(user_id, draft['username'], draft['fecha'], draft['texto'], "pendiente")
    elif tipo == 'photo':
        conf_id = guardar_confesion_media(user_id, draft['username'], draft['fecha'], "pendiente", 'photo', draft['file_id'], draft.get('texto') or "", None)
    elif tipo == 'poll':
        extra = json.dumps({
            'options': draft.get('options', []),
            'multiple': bool(draft.get('multiple', False))
        })
        conf_id = guardar_confesion_media(user_id, draft['username'], draft['fecha'], "pendiente", 'poll', None, draft.get('question') or "", extra)
    else:
        conf_id = guardar_confesion(user_id, draft['username'], draft['fecha'], draft.get('texto') or "", "pendiente")

    # Registrar Anti-Spam (5 minutos)
    registrar_tiempo_confesion(user_id)

    editar_mensaje_principal(
        call.message.chat.id,
        user_id,
        "✅ <b>¡Confesión enviada exitosamente! 🎉</b>\n\n⏳ Nuestro equipo de moderación la revisará en breve.\nTe notificaremos en cuanto sea aprobada o rechazada.",
        reply_markup=markup_back()
    )

    safe_username = escape_html(draft['username'])
    tipo_humano = 'Texto' if tipo == 'text' else ('Foto' if tipo == 'photo' else ('Encuesta' if tipo == 'poll' else tipo))

    if tipo == 'text':
        safe_text = escape_html(draft['texto'])
        contenido_admin = f"💬 Contenido:\n{safe_text}"
        chars = len(draft['texto'])
    elif tipo == 'photo':
        safe_caption = escape_html(draft.get('texto') or "")
        contenido_admin = f"📷 Foto\n💬 Caption: {safe_caption}"
        chars = len(draft.get('texto') or "")
    elif tipo == 'poll':
        safe_question = escape_html(draft.get('question') or "")
        opciones = draft.get('options', [])
        opciones_txt = "\n".join([f"• {escape_html(o)}" for o in opciones])
        contenido_admin = f"📊 Encuesta:\n❓ Pregunta: {safe_question}\n🔢 Opciones:\n{opciones_txt}"
        chars = len(draft.get('question') or "")
    else:
        safe_text = escape_html(draft.get('texto') or "")
        contenido_admin = f"💬 Contenido:\n{safe_text}"
        chars = len(draft.get('texto') or "")

    mensaje_admin = p(
        f"🕵️ <b>Nueva Confesión Pendiente #{conf_id}</b>\n\n"
        f"👤 Usuario: @{safe_username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🕒 Fecha: {draft['fecha']}\n"
        f"📦 Tipo: {tipo_humano} | 📏 Caracteres: {chars}\n\n"
        f"{contenido_admin}"
    )

    if GRUPO_ADMIN_ID:
        try:
            if tipo == 'photo' and draft.get('file_id'):
                bot.send_photo(
                    GRUPO_ADMIN_ID,
                    draft['file_id'],
                    caption=mensaje_admin,
                    reply_markup=markup_admin_moderacion(conf_id),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    GRUPO_ADMIN_ID,
                    mensaje_admin,
                    reply_markup=markup_admin_moderacion(conf_id),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Error enviando confesión #{conf_id} al grupo admin: {e}")

    if user_id in user_drafts:
        del user_drafts[user_id]
    clear_user_state(user_id)
    safe_answer_callback(call.id, "✅ Confesión enviada a moderación")

@bot.callback_query_handler(func=lambda c: c.data == "editar_confesion")
@verificar_baneo_handler
def editar_confesion_callback(call):
    user_id = call.from_user.id
    set_user_state(user_id, 'awaiting_confession')
    editar_mensaje_principal(call.message.chat.id, user_id, "✏️ <b>Edita tu confesión:</b> Envía la nueva versión actualizada:", reply_markup=markup_back())
    safe_answer_callback(call.id, "✏️ Modo edición activo")

@bot.callback_query_handler(func=lambda c: c.data == "cancelar_confesion")
@verificar_baneo_handler
def cancelar_confesion(call):
    user_id = call.from_user.id
    if user_id in user_drafts:
        del user_drafts[user_id]
    clear_user_state(user_id)
    editar_mensaje_principal(call.message.chat.id, user_id, "❌ <b>Confesión cancelada.</b> Tu borrador ha sido eliminado.", reply_markup=markup_back())
    safe_answer_callback(call.id, "❌ Cancelado")

# --- Moderación: Aceptar / Rechazar con Motivos / 1-Click Warn & Ban ---

@bot.callback_query_handler(func=lambda c: c.data.startswith("aceptar_"))
def callback_aceptar_confesion(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "⛔ No tienes permiso.")
        return
    conf_id = int(call.data.split("_")[1])
    publicar_confesion(conf_id, call)

def publicar_confesion(confesion_id, call):
    info = actualizar_estado_confesion(confesion_id, "aceptada")
    if not info:
        safe_answer_callback(call.id, "⚠️ No se encontró la confesión")
        return
    texto = info["confesion"]
    user_id = info["user_id"]
    tipo = (info.get('tipo') or 'text')
    file_id = info.get('file_id')
    extra = info.get('extra')

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot_tag = ""
    try:
        me = bot.get_me()
        if me and me.username:
            bot_tag = f"\n\n🤖 @{me.username}"
    except Exception:
        pass

    try:
        if tipo == 'photo' and file_id:
            caption = p(f"{escape_html(texto)}\n\n💭 <b>Confesión Anónima</b>{bot_tag}")
            bot.send_photo(CANAL_ID, file_id, caption=caption, parse_mode="HTML")
        elif tipo == 'poll':
            opts = []
            multiple = False
            if extra:
                try:
                    data = json.loads(extra)
                    opts = data.get('options', [])
                    multiple = bool(data.get('multiple', False))
                except Exception:
                    pass
            if not opts:
                bot.send_message(CANAL_ID, p(f"{escape_html(texto)}{bot_tag}"), parse_mode="HTML")
            else:
                bot.send_poll(CANAL_ID, texto, opts, is_anonymous=True, allows_multiple_answers=multiple)
        else:
            bot.send_message(CANAL_ID, p(f"💭 <b>Confesión Anónima:</b>\n\n{escape_html(texto)}{bot_tag}"), parse_mode="HTML")
    except Exception as e:
        safe_answer_callback(call.id, "⚠️ Error publicando en canal")
        logger.error(f"Error publicando en canal: {e}")
        return

    safe_answer_callback(call.id, "✅ Publicada exitosamente")

    try:
        msg = bot.send_message(
            user_id,
            p("✅ <b>¡Tu confesión ha sido aceptada!</b>\n\nHa sido publicada de forma anónima en el canal principal."),
            parse_mode="HTML"
        )
        registrar_notificacion_pendiente(user_id, user_id, msg.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("menu_rechazo_"))
def callback_menu_rechazo(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "⛔ No tienes permiso.")
        return
    conf_id = int(call.data.split("_")[2])
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup_menu_rechazo(conf_id)
        )
        safe_answer_callback(call.id, "Selecciona el motivo")
    except Exception as e:
        logger.error(f"Error desplegando motivos de rechazo: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("mod_volver_"))
def callback_mod_volver(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "⛔ No tienes permiso.")
        return
    conf_id = int(call.data.split("_")[2])
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup_admin_moderacion(conf_id)
        )
        safe_answer_callback(call.id, "Volviendo a moderación")
    except Exception as e:
        logger.error(f"Error volviendo a moderación: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("motivo_"))
def callback_ejecutar_rechazo_con_motivo(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "⛔ No tienes permiso.")
        return
    parts = call.data.split("_")
    conf_id = int(parts[1])
    clave = parts[2]
    motivo_texto = MOTIVOS_RECHAZO.get(clave, "No cumple con las reglas del canal.")

    info = actualizar_estado_confesion(conf_id, "rechazada", motivo_texto)
    if not info:
        safe_answer_callback(call.id, "⚠️ Confesión no encontrada")
        return
    user_id = info["user_id"]

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    safe_answer_callback(call.id, "❌ Confesión rechazada")

    try:
        msg_text = (
            f"❌ <b>Tu confesión #{conf_id} ha sido rechazada</b>\n\n"
            f"📋 <b>Motivo:</b> {escape_html(motivo_texto)}\n\n"
            "💡 <i>Por favor, revisa las reglas antes de enviar una nueva confesión.</i>"
        )
        msg = bot.send_message(user_id, p(msg_text), parse_mode="HTML")
        registrar_notificacion_pendiente(user_id, user_id, msg.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("qwarn_"))
def callback_quick_warn(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "⛔ No tienes permiso.")
        return
    conf_id = int(call.data.split("_")[1])
    info = actualizar_estado_confesion(conf_id, "rechazada", "Advertencia aplicada por infracción")
    if not info:
        safe_answer_callback(call.id, "⚠️ Confesión no encontrada")
        return
    user_id = info["user_id"]
    username = info["username"]

    agregar_advertencia(user_id, username, f"Infracción en confesión #{conf_id}", call.from_user.id)
    count = contar_advertencias_usuario(user_id)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    if count >= 3:
        banear_usuario(user_id, username, "3 advertencias acumuladas")
        safe_answer_callback(call.id, f"🚫 Usuario @{username} BANEADO (3/3 strikes)", show_alert=True)
        try:
            bot.send_message(user_id, p("🚫 <b>Has sido BANEADO del bot</b>\n\n⚠️ Razón: Has acumulado 3 advertencias por incumplir las reglas."), parse_mode="HTML")
        except Exception:
            pass
    else:
        safe_answer_callback(call.id, f"⚠️ Advertencia aplicada ({count}/3)", show_alert=True)
        try:
            bot.send_message(user_id, p(f"⚠️ <b>Has recibido una advertencia ({count}/3)</b>\n\nTu confesión #{conf_id} violó las normas.\nA la 3ª advertencia serás baneado permanentemente."), parse_mode="HTML")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("qban_"))
def callback_quick_ban(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "⛔ No tienes permiso.")
        return
    conf_id = int(call.data.split("_")[1])
    info = actualizar_estado_confesion(conf_id, "rechazada", "Baneo directo por infracción grave")
    if not info:
        safe_answer_callback(call.id, "⚠️ Confesión no encontrada")
        return
    user_id = info["user_id"]
    username = info["username"]

    banear_usuario(user_id, username, f"Baneo directo por confesión #{conf_id}")

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    safe_answer_callback(call.id, f"🚫 Usuario @{username} baneado", show_alert=True)
    try:
        bot.send_message(user_id, p("🚫 <b>Has sido baneado del bot</b>\n\nTu última confesión fue considerada una infracción grave."), parse_mode="HTML")
    except Exception:
        pass

# --- Comandos Admin ---

@bot.message_handler(commands=["estadisticas"])
def cmd_estadisticas(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, p("🚫 No tienes permiso."))
        return

    uptime = datetime.now() - BOT_START_TIME
    dias = uptime.days
    horas = uptime.seconds // 3600
    minutos = (uptime.seconds % 3600) // 60

    stats = contar_confesiones()
    tipos = contar_confesiones_por_tipo()
    total_usuarios = contar_usuarios()
    tasa = round((stats['aceptadas']/stats['total']*100) if stats['total']>0 else 0, 1)

    texto = (
        "📊 <b>Estadísticas Generales</b>\n\n"
        f"🏷️ <b>Versión:</b> {BOT_VERSION}\n"
        f"⏱️ <b>Tiempo activo:</b> {dias}d {horas}h {minutos}m\n"
        f"📅 <b>Iniciado:</b> {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"👥 Usuarios registrados: {total_usuarios}\n"
        f"📌 Confesiones totales: {stats['total']}\n"
        f"⏳ Pendientes: {stats['pendientes']}\n"
        f"✅ Aceptadas: {stats['aceptadas']}\n"
        f"❌ Rechazadas: {stats['rechazadas']}\n\n"
        f"🗂️ Por tipo:\n"
        f"💬 Texto: {tipos.get('text', 0)} | 📷 Foto: {tipos.get('photo', 0)} | 📊 Encuesta: {tipos.get('poll', 0)}\n\n"
        f"📈 Tasa de aceptación: {tasa}%\n"
        f"✅ <b>Estado:</b> Operativo"
    )
    bot.send_message(message.chat.id, p(texto), parse_mode="HTML")

@bot.message_handler(commands=["global"])
def cmd_global(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, p("🚫 No tienes permiso."))
        return
    msg = message.text.partition(' ')[2].strip()
    if not msg:
        bot.reply_to(message, p("⚠️ Usa: /global mensaje"))
        return
    usuarios = obtener_todos_usuarios()
    enviados = 0
    for uid in usuarios:
        try:
            bot.send_message(uid, p(f"📢 <b>Mensaje Global:</b>\n\n{escape_html(msg)}"), parse_mode="HTML")
            enviados += 1
        except Exception:
            pass
    bot.reply_to(message, p(f"✅ Mensaje global enviado a {enviados} usuarios."))

@bot.message_handler(commands=["limpiar_confesiones"])
def cmd_limpiar_confesiones(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, p("🚫 No tienes permiso."))
        return
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, p("⚠️ Usa: /limpiar_confesiones dias"))
        return
    dias = int(args[1])
    eliminadas = limpiar_confesiones_antiguas(dias)
    bot.reply_to(message, p(f"🧹 Se eliminaron {eliminadas} confesiones con más de {dias} días."))

@bot.message_handler(commands=["advertencia"])
def cmd_advertencia(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, p("🚫 No tienes permiso."))
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        bot.reply_to(message, p("⚠️ Usa: /advertencia <user_id o @username> [razon]"))
        return

    identificador = args[1]
    razon = args[2] if len(args) > 2 else "Incumplimiento de reglas"

    if identificador.isdigit():
        user_id = int(identificador)
        username = obtener_username_por_user_id(user_id) or str(user_id)
    else:
        user_id = obtener_user_id_por_username(identificador)
        if not user_id:
            bot.reply_to(message, p(f"❌ Usuario {identificador} no encontrado en la base de datos."))
            return
        username = identificador.lstrip('@')

    try:
        agregar_advertencia(user_id, username, razon, message.from_user.id)
        count = contar_advertencias_usuario(user_id)
        if count >= 3:
            banear_usuario(user_id, username, razon)
            bot.reply_to(message, p(f"🚫 <b>Usuario BANEADO</b>\n\n👤 @{username} (ID: {user_id})\n⚠️ Razón: {escape_html(razon)}\n📊 Advertencias: {count}/3"), parse_mode="HTML")
            try:
                bot.send_message(user_id, p(f"🚫 <b>Has sido Baneado</b>\n\n⚠️ Razón: {escape_html(razon)}"), parse_mode="HTML")
            except Exception:
                pass
        else:
            bot.reply_to(message, p(f"⚠️ <b>Advertencia enviada</b>\n\n👤 @{username} (ID: {user_id})\n📊 Advertencias: {count}/3\n⚠️ Razón: {escape_html(razon)}"), parse_mode="HTML")
            try:
                bot.send_message(user_id, p(f"⚠️ <b>Has recibido una Advertencia ({count}/3)</b>\n\n{escape_html(razon)}\n\nA la 3ª serás baneado."), parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=["banear"])
def cmd_banear(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, p("🚫 No tienes permiso."))
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        bot.reply_to(message, p("⚠️ Usa: /banear <user_id o @username> [razon]"))
        return

    identificador = args[1]
    razon = args[2] if len(args) > 2 else "Ban directo por administrador"

    if identificador.isdigit():
        user_id = int(identificador)
        username = obtener_username_por_user_id(user_id) or str(user_id)
    else:
        user_id = obtener_user_id_por_username(identificador)
        if not user_id:
            bot.reply_to(message, p(f"❌ Usuario {identificador} no encontrado en la base de datos."))
            return
        username = identificador.lstrip('@')

    try:
        banear_usuario(user_id, username, razon)
        bot.reply_to(message, p(f"🚫 <b>Usuario baneado</b>\n\n👤 @{username} (ID: {user_id})\n⚠️ Razón: {escape_html(razon)}"), parse_mode="HTML")
        try:
            bot.send_message(user_id, p(f"🚫 <b>Has sido Baneado</b>\n\n{escape_html(razon)}"), parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=["desbanear"])
def cmd_desbanear(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, p("🚫 No tienes permiso."))
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, p("⚠️ Usa: /desbanear <user_id o @username>"))
        return

    identificador = args[1]
    if identificador.isdigit():
        user_id = int(identificador)
        username = obtener_username_por_user_id(user_id) or str(user_id)
    else:
        user_id = obtener_user_id_por_username(identificador)
        if not user_id:
            bot.reply_to(message, p(f"❌ Usuario {identificador} no encontrado."))
            return
        username = identificador.lstrip('@')

    try:
        desbanear_usuario(user_id)
        bot.reply_to(message, p(f"✅ <b>Usuario desbaneado</b>\n\n👤 @{username} (ID: {user_id})"), parse_mode="HTML")
        try:
            bot.send_message(user_id, p("✅ <b>Has sido desbaneado</b>\n\nYa puedes volver a enviar confesiones respetando las reglas."), parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=["appeal"])
def cmd_appeal(message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3 or not args[1].isdigit():
        bot.reply_to(message, p("⚠️ Usa: /appeal <confesion_id> motivo_de_apelacion"))
        return
    conf_id = int(args[1])
    razon = args[2].strip()
    try:
        appeal_id = crear_appeal(message.from_user.id, message.from_user.username or message.from_user.first_name or "SinUsername", conf_id, razon)
        bot.reply_to(message, p(f"✅ <b>Apelación registrada (#{appeal_id})</b>. Los administradores la revisarán."), parse_mode="HTML")
        if GRUPO_ADMIN_ID:
            try:
                bot.send_message(GRUPO_ADMIN_ID, p(f"🧾 <b>Nueva apelación #{appeal_id}</b> de @{message.from_user.username or 'SinUsername'}\nConfesión: #{conf_id}\nMotivo: {escape_html(razon)}"), parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ Error registrando apelación: {e}")

@bot.callback_query_handler(func=lambda c: c.data in ("estadisticas_avanzadas", "sistema_appeals", "reportes_automaticos"))
def admin_features_callback(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "🚫 No tienes permiso")
        return

    if call.data == "estadisticas_avanzadas":
        push_page(call.from_user.id, 'estadisticas_avanzadas')
        stats = contar_confesiones()
        total_usuarios = contar_usuarios()
        texto = (
            f"📊 <b>Estadísticas Avanzadas</b>\n\n👥 Usuarios registrados: {total_usuarios}\n"
            f"📌 Total confesiones: {stats['total']}\n⏳ Pendientes: {stats['pendientes']}\n✅ Aceptadas: {stats['aceptadas']}\n❌ Rechazadas: {stats['rechazadas']}\n"
        )
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, texto, reply_markup=markup_back())
        safe_answer_callback(call.id, "📊 Estadísticas cargadas")

    elif call.data == "sistema_appeals":
        push_page(call.from_user.id, 'sistema_appeals')
        appeals = obtener_appeals_pendientes()
        if not appeals:
            editar_mensaje_principal(call.message.chat.id, call.from_user.id, "✅ No hay apelaciones pendientes.", reply_markup=markup_back())
            safe_answer_callback(call.id, "✅ Sin apelaciones")
            return
        a = appeals[0]
        texto = (
            f"🧾 <b>Apelación ID:</b> #{a['id']}\n👤 Usuario: @{escape_html(a['username'])} (ID: {a['user_id']})\n"
            f"🕒 Fecha: {a['fecha']}\n⤏ Razón:\n{escape_html(a['razon'])}"
        )
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Aceptar Apelación", callback_data=f"appeal_aceptar_{a['id']}"),
            InlineKeyboardButton("❌ Rechazar Apelación", callback_data=f"appeal_rechazar_{a['id']}")
        )
        markup.add(InlineKeyboardButton("◀️ Atrás", callback_data="volver_atras"))
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, texto, reply_markup=markup)
        safe_answer_callback(call.id, f"🧾 {len(appeals)} apelaciones pendientes")

    elif call.data == "reportes_automaticos":
        push_page(call.from_user.id, 'reportes_automaticos')
        stats = contar_confesiones()
        total_usuarios = contar_usuarios()
        texto = (
            f"📈 <b>Reporte General</b>\n\n👥 Usuarios: {total_usuarios}\n📌 Confesiones: {stats['total']}\n⏳ Pendientes: {stats['pendientes']}\n✅ Aceptadas: {stats['aceptadas']}\n❌ Rechazadas: {stats['rechazadas']}"
        )
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, texto, reply_markup=markup_back())
        safe_answer_callback(call.id, "📈 Reporte generado")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("appeal_aceptar_", "appeal_rechazar_")))
def appeal_resolve_callback(call):
    if not is_admin(call.from_user.id):
        safe_answer_callback(call.id, "🚫 No tienes permiso")
        return
    try:
        parts = call.data.split("_")
        accion = parts[1]
        appeal_id = int(parts[2])
    except Exception:
        safe_answer_callback(call.id, "⚠️ Datos inválidos")
        return

    if accion == "aceptar":
        resolver_appeal(appeal_id, call.from_user.id, 'aceptar')
        safe_answer_callback(call.id, "✅ Apelación aceptada")
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, f"✅ Apelación #{appeal_id} aceptada favorablemente.", reply_markup=markup_back())
    else:
        resolver_appeal(appeal_id, call.from_user.id, 'rechazar')
        safe_answer_callback(call.id, "❌ Apelación rechazada")
        editar_mensaje_principal(call.message.chat.id, call.from_user.id, f"❌ Apelación #{appeal_id} rechazada.", reply_markup=markup_back())

@bot.callback_query_handler(func=lambda c: c.data == "volver_menu")
@verificar_baneo_handler
def volver_menu_callback(call):
    user_id = call.from_user.id
    user_page_stack[user_id] = []
    user_is_admin = is_admin(user_id)
    nombre = obtener_nombre_usuario(call.from_user)
    texto_bienvenida = (
        f"👋 ¡Hola, {nombre}!\n\n"
        "💭 <b>Confesiones Anónimas</b>\n"
        "Envía confesiones al canal de forma 100% anónima.\n\n"
        "🚀 Usa los botones interactivos para comenzar."
    )
    editar_mensaje_principal(call.message.chat.id, user_id, texto_bienvenida, reply_markup=markup_start(user_is_admin))
    safe_answer_callback(call.id, "🏠 Volviendo al menú")

@bot.message_handler(func=lambda message: True)
@verificar_baneo_handler
def echo_all(message):
    user_id = message.from_user.id
    eliminar_notificacion_pendiente(user_id)

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    editar_mensaje_principal(
        message.chat.id,
        user_id,
        "👋 ¡Hola! Usa los botones interactivos del menú para navegar.",
        reply_markup=markup_back()
    )

def limpiar_estados_expirados():
    while True:
        time.sleep(300)
        try:
            current_time = time.time()
            users_to_clean = []
            for user_id, timestamp in list(user_states_timestamp.items()):
                if current_time - timestamp > STATE_TIMEOUT_MINUTES * 60:
                    users_to_clean.append(user_id)
            for user_id in users_to_clean:
                clear_user_state(user_id)
                if user_id in user_drafts:
                    del user_drafts[user_id]
        except Exception as e:
            logger.error(f"Error limpiando estados expirados: {e}")

threading.Thread(target=limpiar_estados_expirados, daemon=True).start()

if __name__ == "__main__":
    try:
        bot_info = bot.get_me()
        logger.info(f"Bot iniciado: @{bot_info.username}")
        
        # Registrar comandos de BotFather automáticamente
        try:
            bot.set_my_commands([
                types.BotCommand("start", "Iniciar el bot y abrir el menú"),
                types.BotCommand("appeal", "Apelar una confesión o baneo")
            ])
            logger.info("Comandos registrados automáticamente en Telegram")
        except Exception as e:
            logger.warning(f"No se pudieron registrar comandos automáticos: {e}")

        logger.info("🚀 Bot de confesiones activo")

        telebot.apihelper.RETRY_ON_ERROR = True

        while True:
            try:
                bot.infinity_polling(
                    skip_pending=True,
                    timeout=20,
                    long_polling_timeout=20,
                    restart_on_change=False,
                    logger_level=logging.WARNING
                )
            except KeyboardInterrupt:
                print("\nBot detenido por usuario", flush=True)
                sys.exit(0)
            except Exception as polling_error:
                error_str = str(polling_error).lower()
                if "conflict" in error_str or "409" in error_str:
                    logger.error(f"Conflicto de polling detectado: {polling_error}")
                    sys.exit(1)

                logger.warning(f"Reconectando polling tras desconexion temporal: {polling_error}")
                time.sleep(3)
                continue
    except KeyboardInterrupt:
        print("\nBot detenido por usuario", flush=True)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

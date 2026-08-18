"""
Módulo de Emojis Premium Dinámicos y Animados para Telegram.
Transforma automáticamente cualquier emoji unicode dentro de textos HTML por
la etiqueta <tg-emoji emoji-id="ID">emoji</tg-emoji> respetando etiquetas HTML.
"""
import re

EMOJI_MAP_CORE = {
    # --- Dispositivos y Plataformas ---
    "💻": "5431376038628171216",  # Laptop animado (Windows)
    "📱": "5407025283456835913",  # Smartphone animado (Móvil)
    "🖥️": "5282843764451195532",  # Monitor Desktop
    "🖥": "5282843764451195532",
    "🤖": "5372981976804366741",  # Robot animado (Bot)
    "🎮": "5467583879948803288",  # Consola

    # --- Acciones y Estados de Archivos / Edición ---
    "📥": "5433811242135331842",  # Descarga
    "📤": "5433614747381538714",  # Subida
    "📦": "5433653135799228968",  # Paquete
    "💾": "5431376038628171216",  # Disco
    "📁": "5433653135799228968",  # Carpeta
    "📂": "5431721976769027887",
    "🗂️": "5433653135799228968",
    "🗂": "5433653135799228968",
    "📝": "5334882760735598374",  # Nota / Descripción
    "✏️": "5334882760735598374",  # Lápiz animado
    "✏": "5334882760735598374",
    "✍️": "5334882760735598374",  # Mano escribiendo
    "✍": "5334882760735598374",
    "📖": "5334882760735598374",  # Libro abierto
    "📜": "5334882760735598374",  # Pergamino
    "📋": "5334882760735598374",  # Portapapeles
    "🧾": "5334882760735598374",  # Recibo / Appeal
    "📭": "5433811242135331842",  # Buzón
    "🏷️": "5397782960512444700",  # Tag / Versión
    "🏷": "5397782960512444700",
    "💼": "5359785904535774578",  # Maletín
    "📅": "5413879192267805083",  # Calendario
    "🗓️": "5413879192267805083",
    "🗓": "5413879192267805083",
    "🕒": "5413704112220949842",  # Reloj animado
    "⏱️": "5413704112220949842",  # Cronómetro
    "⏱": "5413704112220949842",
    "🌐": "5447410659077661506",  # Globo
    "🔗": "5375129357373165375",  # Link
    "📎": "5377844313575150051",  # Clip
    "🗑️": "5445267414562389170",  # Papelera
    "🗑": "5445267414562389170",
    "🧹": "5445267414562389170",  # Escoba / Limpieza
    "🔄": "5264727218734524899",  # Recarga
    "🔁": "5264727218734524899",  # Repetir
    "📷": "5431376038628171216",  # Cámara / Foto
    "📸": "5431376038628171216",
    "📏": "5350460637182993292",  # Regla / Longitud
    "🔢": "5397782960512444700",  # Números
    "🆔": "5397782960512444700",  # ID Tag

    # --- Usuarios y Perfiles ---
    "👤": "5359785904535774578",  # Usuario individual
    "👥": "5359785904535774578",  # Grupo usuarios
    "👨‍💻": "5359785904535774578",
    "🕵️": "5188217332748527444",  # Detective / Moderador
    "🕵": "5188217332748527444",

    # --- Seguridad, Moderación y Rendimiento ---
    "🔒": "5296369303661067030",  # Candado
    "🔏": "5296369303661067030",  # Candado y pluma
    "🛡️": "5251203410396458957",  # Escudo
    "🛡": "5251203410396458957",
    "⚖️": "5251203410396458957",  # Balanza de justicia
    "⚖": "5251203410396458957",
    "⚡️": "5456140674028019486",  # Rayo
    "⚡": "5456140674028019486",
    "💎": "5427168083074628963",  # Diamante
    "👑": "5467406098367521267",  # Corona
    "🔥": "5420315771991497307",  # Fuego
    "✨": "5472164874886846699",  # Brillos
    "🎉": "5461151367559141950",  # Fiesta
    "🚀": "5445284980978621387",  # Cohete

    # --- Búsqueda, Estadísticas y Menús ---
    "🔍": "5188217332748527444",  # Lupa
    "🔎": "5188311512791393083",
    "📊": "5431577498364158238",  # Gráfico barras
    "📈": "5373001317042101552",  # Tendencia alza
    "📉": "5361748661640372834",
    "🏠": "5416041192905265756",  # Casa
    "📣": "5424818078833715060",  # Megáfono
    "📢": "5424818078833715060",
    "💬": "5443038326535759644",  # Mensaje
    "💭": "5467538555158943525",  # Pensamiento
    "📌": "5397782960512444700",  # Pin
    "📍": "5391032818111363540",
    "🎯": "5350460637182993292",  # Diana
    "📺": "5282843764451195532",

    # --- Reacciones, Insignias y Logros ---
    "⭐": "5438496463044752972",  # Estrella dorada
    "⭐️": "5438496463044752972",
    "🌟": "5458799228719472718",  # Estrella radiante
    "❤️": "5449505950283078474",  # Corazón
    "👍": "5469770542288478598",  # Like
    "👋": "5472055112702629499",  # Saludo
    "👀": "5210956306952758910",  # Ojos
    "🏆": "5440539497383087970",  # Trofeo
    "🥇": "5440539497383087970",  # Medalla oro (Puesto 1)
    "🥈": "5447203607294265305",  # Medalla plata (Puesto 2)
    "🥉": "5453902265922376865",  # Medalla bronce (Puesto 3)
    "1️⃣": "5440539497383087970",  # 1 animado
    "2️⃣": "5447203607294265305",  # 2 animado
    "3️⃣": "5453902265922376865",  # 3 animado
    "4️⃣": "5280889245093871939",  # 4 bloque
    "5️⃣": "5280889245093871939",  # 5 bloque

    # --- Alertas y Notificaciones ---
    "🔔": "5242628160297641831",  # Campana
    "💡": "5472146462362048818",  # Bombilla
    "🚨": "5395695537687123235",  # Sirena
    "⚠️": "5447644880824181073",  # Advertencia
    "⚠": "5447644880824181073",
    "🚫": "5240241223632954241",  # Prohibido
    "⛔️": "5260293700088511294",  # Stop
    "⛔": "5260293700088511294",
    "❌": "5465665476971471368",  # Cruz roja
    "✅": "5427009714745517609",  # Check verde
    "✔️": "5188216731453103384",
    "✔": "5188216731453103384",
    "❗️": "5467928559664242360",
    "❗": "5467928559664242360",
    "‼️": "5467890025217661107",
    "❓": "5467666648263564704",  # Interrogación
    "⁉️": "5467596412663372909",
    "ℹ️": "5334544901428229844",  # Información
    "ℹ": "5334544901428229844",
    "⏰": "5413704112220949842",  # Alarma
    "⏳": "5451732530048802485",  # Reloj arena
    "⌛": "5451732530048802485",

    # --- Navegación y Herramientas ---
    "◀️": "5416117059207572332",  # Flecha atrás
    "◀": "5416117059207572332",
    "➡️": "5416117059207572332",
    "⬅️": "5416117059207572332",
    "🛠️": "5341715473882955310",  # Herramientas
    "🛠": "5341715473882955310",
    "⚙️": "5341715473882955310",  # Engranaje
    "⚙": "5341715473882955310",
    "🔧": "5341715473882955310",
}

def _build_final_emoji_map() -> dict[str, str]:
    """Carga y genera el mapa completo de emojis con soporte dual para variation selectors."""
    mapping = {}
    for em_char, em_id in EMOJI_MAP_CORE.items():
        mapping[em_char] = em_id
        clean = em_char.replace("\ufe0f", "")
        mapping[clean] = em_id
        mapping[clean + "\ufe0f"] = em_id
    return mapping

EMOJI_MAP = _build_final_emoji_map()

_ESCAPED_KEYS = [re.escape(k) for k in sorted(EMOJI_MAP.keys(), key=lambda x: len(x), reverse=True) if k]
_EMOJI_REGEX_PATTERN = re.compile("|".join(_ESCAPED_KEYS)) if _ESCAPED_KEYS else None
_HTML_TAG_REGEX = re.compile(r'<[^>]+>')

def parse_emojis(text: str) -> str:
    """
    Reemplaza todos los emojis soportados dentro del texto HTML por
    la etiqueta <tg-emoji emoji-id="ID">emoji</tg-emoji> respetando etiquetas HTML.
    """
    if not text or not _EMOJI_REGEX_PATTERN:
        return text

    segments = []
    last_idx = 0

    for match in _HTML_TAG_REGEX.finditer(text):
        start, end = match.span()
        if start > last_idx:
            plain_part = text[last_idx:start]
            segments.append(_replace_in_plain_text(plain_part))
        segments.append(match.group(0))
        last_idx = end

    if last_idx < len(text):
        segments.append(_replace_in_plain_text(text[last_idx:]))

    return "".join(segments)

def _replace_in_plain_text(plain: str) -> str:
    if not _EMOJI_REGEX_PATTERN:
        return plain
    return _EMOJI_REGEX_PATTERN.sub(
        lambda m: f'<tg-emoji emoji-id="{EMOJI_MAP[m.group(0)]}">{m.group(0)}</tg-emoji>',
        plain
    )

p = parse_emojis

"""
Módulo de Emojis Premium Dinámicos y Animados.
Construido EXCLUSIVAMENTE a partir de los paquetes oficiales:
1. RestrictedEmoji (https://t.me/addemoji/RestrictedEmoji - 997 Emojis Animados)
2. NewsEmoji (https://t.me/addemoji/NewsEmoji - 100 Emojis Animados de Noticias)
3. @devaiden (Badges y Puntos de Énfasis)

Transforma automáticamente cualquier emoji unicode en su correspondiente etiqueta
<tg-emoji emoji-id="ID">emoji</tg-emoji> respetando el formato HTML de Telegram.
"""
import os
import json
import re

# Mapeo Meticuloso y Creativo (Cero repeticiones innecesarias, 100% contextual)
EMOJI_MAP_CORE = {
    # --- Dispositivos y Plataformas ---
    "💻": "5431376038628171216",  # Laptop animado (PC / Windows)
    "📱": "5407025283456835913",  # Smartphone animado (Android / APK)
    "🖥️": "5282843764451195532",  # Monitor Desktop (Requisitos de Sistema)
    "🖥": "5282843764451195532",
    "🤖": "5372981976804366741",  # Robot animado (Automatización / Bot)
    "🎮": "5467583879948803288",  # Consola de videojuegos (Juegos)

    # --- Acciones y Estados de Archivos ---
    "📥": "5433811242135331842",  # Bandeja de Descarga animada
    "📤": "5433614747381538714",  # Bandeja de Subida animada
    "📦": "5433653135799228968",  # Paquete / Carpeta animada limpia
    "💾": "5431376038628171216",  # Disco / Almacenamiento animado
    "💽": "5431376038628171216",
    "💿": "5431376038628171216",
    "📁": "5433653135799228968",  # Carpeta animada (Categorías)
    "📂": "5431721976769027887",  # Carpeta abierta
    "🗂️": "5433653135799228968",
    "🗂": "5433653135799228968",
    "📝": "5334882760735598374",  # Hoja y lápiz (Descripción)
    "🏷️": "5397782960512444700",  # Tag / Pin animado (Versión)
    "🏷": "5397782960512444700",
    "💼": "5359785904535774578",  # Maletín profesional (Desarrollador / Publisher)
    "📅": "5413879192267805083",  # Calendario animado (Lanzamiento / Fechas)
    "🗓️": "5413879192267805083",
    "🗓": "5413879192267805083",
    "🌐": "5447410659077661506",  # Globo terráqueo girando (Idiomas)
    "🔗": "5375129357373165375",  # Eslabones de enlace directo
    "📎": "5377844313575150051",  # Clip de archivo adjunto
    "🗑️": "5445267414562389170",  # Papelera animada (Eliminar)
    "🗑": "5445267414562389170",
    "🔄": "5264727218734524899",  # Flechas de recarga animadas

    # --- Seguridad, Claves y Rendimiento ---
    "🔒": "5296369303661067030",  # Candado animado (Contraseña: 123)
    "🛡️": "5251203410396458957",  # Escudo protector (Antivirus / Verificado)
    "🛡": "5251203410396458957",
    "⚡️": "5456140674028019486",  # Rayo de energía (Alta velocidad / Conexiones)
    "⚡": "5456140674028019486",
    "💎": "5427168083074628963",  # Diamante resplandeciente (MOD / Premium)
    "👑": "5467406098367521267",  # Corona dorada (Top / Admin / VIP)
    "🔥": "5420315771991497307",  # Fuego animado (Popular / Destacado)
    "✨": "5472164874886846699",  # Estrellas de brillo (Calidad / Nuevo)
    "🎉": "5461151367559141950",  # Confeti de fiesta (¡Pedido listo!)
    "🚀": "5445284980978621387",  # Cohete despegando (Procesamiento rápido)

    # --- Búsqueda, Estadísticas y Navegación ---
    "🔍": "5188217332748527444",  # Lupa animada (Búsqueda en catálogo)
    "🔎": "5188311512791393083",  # Lupa secundaria
    "📊": "5431577498364158238",  # Gráfico de barras (Estadísticas del bot)
    "📈": "5373001317042101552",  # Tendencia al alza
    "📉": "5361748661640372834",  # Tendencia
    "🏠": "5416041192905265756",  # Casa / Home animada (Menú Principal)
    "📣": "5424818078833715060",  # Megáfono animado (Canal Oficial / Anuncios)
    "📢": "5424818078833715060",
    "💬": "5443038326535759644",  # Mensaje / Ayuda
    "💭": "5467538555158943525",  # Pensamiento
    "📌": "5397782960512444700",  # Pin animado
    "📍": "5391032818111363540",  # Ubicación animada
    "🎯": "5350460637182993292",  # Diana de puntería (Objetivo)

    # --- Favoritos y Reacciones ---
    "⭐": "5438496463044752972",  # Estrella dorada (Guardar en Favoritos)
    "⭐️": "5438496463044752972",
    "🌟": "5458799228719472718",  # Estrella radiante (En Favoritos)
    "❤️": "5449505950283078474",  # Corazón animado
    "👍": "5469770542288478598",  # Pulgar arriba animado
    "👋": "5472055112702629499",  # Mano saludando (Bienvenida / Start)
    "👀": "5210956306952758910",  # Ojos curiosos (Mirar catálogo)

    # --- Alertas, Notificaciones y Consejos ---
    "🔔": "5242628160297641831",  # Campana dorada animada (Actualizaciones)
    "💡": "5472146462362048818",  # Bombilla encendida (Consejos / Tips)
    "🚨": "5395695537687123235",  # Sirena de emergencia (Alertas del sistema)
    "⚠️": "5447644880824181073",  # Triángulo de advertencia
    "🚫": "5240241223632954241",  # Prohibido / Límite alcanzado
    "⛔️": "5260293700088511294",
    "⛔": "5260293700088511294",
    "❌": "5465665476971471368",  # Cruz roja animada (Error / Cancelar)
    "✅": "5427009714745517609",  # Check verde animado (Éxito / Aprobado)
    "✔️": "5188216731453103384",  # Check animado
    "✔": "5188216731453103384",
    "❗️": "5467928559664242360",  # Exclamación roja animada
    "❗": "5467928559664242360",
    "‼️": "5467890025217661107",  # Doble exclamación
    "❓": "5467666648263564704",  # Interrogación azul animada
    "⁉️": "5467596412663372909",  # Interrogación y exclamación
    "ℹ️": "5334544901428229844",  # Información
    "ℹ": "5334544901428229844",
    "⏰": "5413704112220949842",  # Reloj animado (Horarios / Descanso)
    "⏳": "5451732530048802485",  # Reloj de arena animado (En proceso)
    "⌛": "5451732530048802485",

    # --- Badges de Énfasis y Devaiden (@devaiden) ---
    "🔻": "5280935824014199512",  # Flecha roja de énfasis Aiden
    "🛑": "5278566393636212269",  # Señal Stop de Aiden
    "🕳️": "5280940316549987697",  # Portal / Viñeta estilizada Aiden
    "🕳": "5280940316549987697",
    "🟥": "5280889245093871939",  # Bloque rojo Aiden

    # --- Badges y Medallas de Ranking ---
    "🥇": "5440539497383087970",  # Medalla de Oro animada (Puesto 1)
    "🥈": "5447203607294265305",  # Medalla de Plata animada (Puesto 2)
    "🥉": "5453902265922376865",  # Medalla de Bronce animada (Puesto 3)
    "🆕": "5361979468887893611",  # Badge NEW animado
    "🔝": "5422354988103901774",  # Badge TOP animado
    "🆓": "5364112491381006601",  # Badge FREE animado
    "💯": "5188208446461188962",  # 100% animado
    "➕": "5226945370684140473",  # Más / Añadir
    "➖": "5229113891081956317",  # Menos
    "➡️": "5416117059207572332",  # Siguiente página / Flecha derecha
    "➡": "5416117059207572332",
    "⬅️": "5416117059207572332",  # Flecha izquierda
    "⬅": "5416117059207572332",
    "↩️": "5416117059207572332",  # Volver
    "↩": "5416117059207572332",
    "🎵": "5188621441926438751",  # Música / Audio
    "🎶": "5188621441926438751",
    "⚙️": "5341715473882955310",  # Ajustes / Engranajes
    "⚙": "5341715473882955310",
    "🔧": "5341715473882955310",  # Herramientas
    "🛠️": "5341715473882955310",
    "🛠": "5341715473882955310",
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

# Expresión regular ordenada por longitud descendente para reemplazo atómico en un solo pase
_ESCAPED_KEYS = [re.escape(k) for k in sorted(EMOJI_MAP.keys(), key=lambda x: len(x), reverse=True) if k]
_EMOJI_REGEX_PATTERN = re.compile("|".join(_ESCAPED_KEYS)) if _ESCAPED_KEYS else None
_HTML_TAG_REGEX = re.compile(r'<[^>]+>')

def parse_emojis(text: str) -> str:
    """
    Reemplaza todos los emojis soportados dentro del texto HTML por
    la etiqueta <tg-emoji emoji-id="ID">emoji</tg-emoji> en una sola pasada.
    Respeta el HTML existente para no alterar tags ni URLs.
    """
    if not text or not _EMOJI_REGEX_PATTERN:
        return text

    segments = []
    last_idx = 0
    
    # Dividimos por etiquetas HTML para procesar solo el texto visible
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

# Shorthand para uso rápido en formateo de strings
p = parse_emojis


"""
Modulo de Emojis Premium Dinamicos y Animados para Telegram.
"""
import re

EMOJI_MAP_CORE = {
    # --- Dispositivos y Plataformas ---
    "💻": "5431376038628171216",  # Laptop animado
    "📱": "5407025283456835913",  # Smartphone animado
    "🖥️": "5282843764451195532",  # Monitor Desktop
    "🖥": "5282843764451195532",
    "🤖": "5372981976804366741",  # Robot animado
    "🎮": "5467583879948803288",  # Consola videojuegos

    # --- Acciones y Estados de Archivos / Edicion ---
    "📥": "5433811242135331842",  # Bandeja de Descarga
    "📤": "5433614747381538714",  # Bandeja de Subida
    "📦": "5433653135799228968",  # Paquete animado
    "💾": "5431376038628171216",  # Disco / Almacenamiento
    "📁": "5431721976769027887",  # Carpeta animada
    "📂": "5431721976769027887",  # Carpeta abierta
    "🗂️": "5433653135799228968",  # Archivador / Panel
    "🗂": "5433653135799228968",
    "📝": "5334882760735598374",  # Hoja y lapiz
    "✍️": "5334882760735598374",  # Mano escribiendo
    "✍": "5334882760735598374",
    "📜": "5334882760735598374",  # Pergamino / Mis Confesiones animado
    "✏️": "5397782960512444700",  # Tag / Editar pin
    "✏": "5397782960512444700",
    "🏷️": "5397782960512444700",  # Tag version
    "🏷": "5397782960512444700",
    "📖": "5334544901428229844",  # Libro abierto / Info
    "📋": "5334544901428229844",  # Portapapeles / Reglas
    "🧾": "5377844313575150051",  # Clip de apelaciones
    "📎": "5377844313575150051",  # Clip adjunto
    "📭": "5361748661640372834",  # Buzon vacio
    "💼": "5359785904535774578",  # Maletin profesional / Perfil
    "📅": "5413879192267805083",  # Calendario animado
    "🗓️": "5413879192267805083",  # Calendario
    "🗓": "5413879192267805083",
    "🕒": "5413879192267805083",  # Hora / Calendario
    "⏱️": "5413704112220949842",  # Cronometro
    "⏱": "5413704112220949842",
    "⏰": "5413704112220949842",  # Alarma reloj
    "🌐": "5447410659077661506",  # Globo terraqueo
    "🔗": "5375129357373165375",  # Eslabones de enlace
    "🗑️": "5445267414562389170",  # Papelera animada
    "🗑": "5445267414562389170",
    "🧹": "5445267414562389170",  # Escoba / Limpieza
    "🔄": "5264727218734524899",  # Flechas de recarga / Verificar
    "🔁": "5264727218734524899",  # Repetir ciclo
    "📷": "5407025283456835913",  # Foto / Smartphone
    "📸": "5467583879948803288",  # Camara flash
    "📏": "5350460637182993292",  # Medida / Longitud
    "🎯": "5350460637182993292",  # Diana punteria
    "🔢": "5361979468887893611",  # Badge NEW (opciones)
    "🆔": "5422354988103901774",  # Badge TOP (ID)

    # --- Usuarios y Perfiles ---
    "👤": "5359785904535774578",  # Usuario
    "👥": "5469770542288478598",  # Grupo usuarios (pulgar/comunidad)
    "👨‍💻": "5445284980978621387",  # Desarrollador / Cohete
    "🕵️": "5188217332748527444",  # Detective / Moderador
    "🕵": "5188217332748527444",
    "🔍": "5188217332748527444",  # Lupa de busqueda
    "🔎": "5188311512791393083",  # Lupa secundaria

    # --- Seguridad, Moderacion y Rendimiento ---
    "🔒": "5296369303661067030",  # Candado animado
    "🔏": "5296369303661067030",  # Candado y pluma
    "🛡️": "5251203410396458957",  # Escudo protector
    "🛡": "5251203410396458957",
    "⚖️": "5251203410396458957",  # Balanza de justicia
    "⚖": "5251203410396458957",
    "⚡️": "5456140674028019486",  # Rayo de energia
    "⚡": "5456140674028019486",
    "💎": "5427168083074628963",  # Diamante resplandeciente
    "👑": "5467406098367521267",  # Corona dorada
    "🔥": "5420315771991497307",  # Fuego animado
    "✨": "5472164874886846699",  # Estrellas de brillo
    "🎉": "5461151367559141950",  # Confeti de fiesta
    "🚀": "5445284980978621387",  # Cohete despegando

    # --- Menus, Estadisticas y Navegacion ---
    "📊": "5431577498364158238",  # Grafico de barras
    "📈": "5373001317042101552",  # Tendencia al alza
    "📉": "5361748661640372834",  # Tendencia a la baja
    "🏠": "5416041192905265756",  # Casa / Home
    "📢": "5424818078833715060",  # Megaono animado
    "📣": "5424818078833715060",  # Megafono
    "💬": "5443038326535759644",  # Bocadillo de mensaje
    "💭": "5467538555158943525",  # Nube de pensamiento
    "📌": "5391032818111363540",  # Pin animado
    "📍": "5391032818111363540",  # Ubicacion pin

    # --- Reacciones, Insignias y Ranking ---
    "⭐": "5438496463044752972",  # Estrella dorada
    "⭐️": "5438496463044752972",
    "🌟": "5458799228719472718",  # Estrella radiante
    "❤️": "5449505950283078474",  # Corazon animado
    "👍": "5469770542288478598",  # Pulgar arriba
    "👋": "5472055112702629499",  # Mano saludando
    "👀": "5210956306952758910",  # Ojos curiosos
    "🏆": "5364112491381006601",  # Badge Trofeo dorado
    "🥇": "5440539497383087970",  # Medalla de Oro animada
    "🥈": "5447203607294265305",  # Medalla de Plata animada
    "🥉": "5453902265922376865",  # Medalla de Bronce animada
    "1️⃣": "5440539497383087970",  # 1st Oro
    "2️⃣": "5447203607294265305",  # 2nd Plata
    "3️⃣": "5453902265922376865",  # 3rd Bronce
    "4️⃣": "5280889245093871939",  # Bloque rojo Aiden 4
    "5️⃣": "5280935824014199512",  # Flecha roja Aiden 5

    # --- Alertas y Notificaciones ---
    "🔔": "5242628160297641831",  # Campana dorada
    "💡": "5472146462362048818",  # Bombilla encendida
    "🚨": "5395695537687123235",  # Sirena de emergencia
    "⚠️": "5447644880824181073",  # Triangulo de advertencia
    "⚠": "5447644880824181073",
    "🚫": "5240241223632954241",  # Senal de prohibido
    "⛔️": "5260293700088511294",  # Stop rojo
    "⛔": "5260293700088511294",
    "🛑": "5278566393636212269",  # Senal Stop de Aiden
    "❌": "5465665476971471368",  # Cruz roja animada
    "✅": "5427009714745517609",  # Check verde animado
    "✔️": "5188216731453103384",  # Check animado blanco/verde
    "✔": "5188216731453103384",
    "❗️": "5467928559664242360",  # Exclamacion roja animada
    "❗": "5467928559664242360",
    "‼️": "5467890025217661107",  # Doble exclamacion
    "❓": "5467666648263564704",  # Interrogacion azul animada
    "⁉️": "5467596412663372909",  # Interrogacion y exclamacion
    "ℹ️": "5188621441926438751",  # Informacion
    "ℹ": "5188621441926438751",
    "⏳": "5451732530048802485",  # Reloj de arena animado
    "⌛": "5451732530048802485",

    # --- Navegacion y Herramientas ---
    "◀️": "5416117059207572332",  # Flecha atras
    "◀": "5416117059207572332",
    "➡️": "5416117059207572332",  # Flecha derecha
    "⬅️": "5416117059207572332",
    "🛠️": "5341715473882955310",  # Herramientas
    "🛠": "5341715473882955310",
    "⚙️": "5341715473882955310",  # Engranajes
    "⚙": "5341715473882955310",
    "🔧": "5341715473882955310",
    "💯": "5188208446461188962",  # 100%
    "➕": "5226945370684140473",  # Mas
    "➖": "5229113891081956317",  # Menos
}

def _build_final_emoji_map() -> dict[str, str]:
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

# 🤖 Bot de Confesiones Universitarias v3.2.0

Bot de confesiones anónimas multimedia para Telegram con moderación avanzada interactiva, sistema anti-spam inteligente, emojis animados premium y persistencia en PostgreSQL con Docker Compose para Dokploy.

---

## ✨ Características Principales

### 👥 Para Usuarios
- ✍️ **Confesiones multimedia**: Texto (hasta 1000 car.), fotos con pie de foto y encuestas interactivas.
- 📱 **Mensaje único editable**: Interfaz fluida y limpia que no satura el chat del usuario.
- ⏳ **Sistema Anti-Spam (Rate Limiting)**: Límite de 1 confesión cada 5 minutos por usuario con contador regresivo en tiempo real.
- 📊 **Estadísticas personales e Insignias**: Contador de confesiones enviadas, aceptadas y badges automáticos.
- 📋 **Reglas comunitarias**: Consulta de normativas antes del envío.
- ⚖️ **Sistema de Apelaciones (/appeal)**: Solicitud de revisión formal para usuarios sancionados o baneados.
- 🎨 **Emojis Animados Premium**: Parseo automático de emojis de Telegram con tags `<tg-emoji>`.

### 🛡️ Para Moderadores y Administradores
- ⚡ **Moderación en 1 Clic**: Aceptar o rechazar confesiones directamente desde el grupo de administradores.
- 📝 **Submenú de Motivos de Rechazo**: Notificación personalizada al usuario explicando la causa del rechazo (Lenguaje ofensivo, Doxxing, Spam, Repetido, etc.).
- ⚠️ **Sanciones Rápidas con 1 Clic**: Botones de `[⚠️ Advertir Autor]` y `[🚫 Banear Autor]` integrados en cada solicitud.
- 🚫 **Sistema de 3 Strikes**: Baneo automático al acumular 3 advertencias.
- 📊 **Comandos de gestión**: `/estadisticas`, `/global <mensaje>`, `/advertencia`, `/banear`, `/desbanear`, `/limpiar_advertencias`.

---

## 🐳 Despliegue en Dokploy con Docker Compose

El proyecto incluye `docker-compose.yml` preconfigurado con **PostgreSQL 16** y un volumen persistente (`confesiones_postgres_data`), garantizando que la base de datos **nunca se borre** al hacer redeploy o actualizar el contenedor.

### Variables de Entorno en Dokploy
```env
BOT_TOKEN=tu_token_de_botfather
CANAL_ID=@TuCanalPublico
GRUPO_ADMIN_ID=-1001234567890
CANAL_OBLIGATORIO=@TuCanalPublico
OWNER_ID=123456789
POSTGRES_PASSWORD=tu_password_seguro_db
```

---

## 🛠️ Tecnologías Utilizadas
- **Python 3.11**
- **pyTelegramBotAPI**
- **PostgreSQL 16** & **psycopg2-binary**
- **Docker & Docker Compose**

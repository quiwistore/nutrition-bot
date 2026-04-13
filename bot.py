import os
import json
import logging
import tempfile
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

DATA_FILE = "nutrition_data.json"

DAILY_GOALS = {
    "calorias": 1900,
    "proteinas": 160,
    "carbohidratos": 160,
    "grasas": 65
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_today_key():
    return date.today().isoformat()

def get_user_today(data, user_id):
    uid = str(user_id)
    today = get_today_key()
    if uid not in data:
        data[uid] = {}
    if today not in data[uid]:
        data[uid][today] = {"comidas": [], "totales": {"calorias": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}
    return data[uid][today]

def analyze_food_with_claude(text):
    prompt = f"""Sos un nutricionista experto. El usuario te dice lo que comió: "{text}"

Analizá los alimentos mencionados y devolvé SOLO un JSON válido con este formato exacto, sin texto extra:
{{
  "descripcion": "descripción corta de lo que comió",
  "calorias": número,
  "proteinas": número en gramos,
  "carbohidratos": número en gramos,
  "grasas": número en gramos,
  "comentario": "un comentario breve nutricional en español rioplatense"
}}

Si no podés identificar comida en el texto, devolvé:
{{"error": "No pude identificar alimentos en el mensaje"}}

Usá valores estimados realistas para porciones típicas argentinas."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

async def transcribe_audio_with_claude(file_path):
    with open(file_path, "rb") as f:
        audio_data = f.read()
    
    import base64
    audio_b64 = base64.b64encode(audio_data).decode()
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Transcribí exactamente lo que dice este audio de voz. Devolvé solo el texto transcripto, sin comentarios."
                },
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "audio/ogg",
                        "data": audio_b64
                    }
                }
            ]
        }]
    )
    return response.content[0].text.strip()

def format_progress(totales):
    lines = []
    for macro, goal_key in [("calorias", "calorias"), ("proteinas", "proteinas"), ("carbohidratos", "carbohidratos"), ("grasas", "grasas")]:
        actual = totales[macro]
        goal = DAILY_GOALS[goal_key]
        pct = min(int((actual / goal) * 100), 100)
        bar_filled = int(pct / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        unit = "kcal" if macro == "calorias" else "g"
        emoji = "🔥" if macro == "calorias" else "💪" if macro == "proteinas" else "🌾" if macro == "carbohidratos" else "🫒"
        lines.append(f"{emoji} *{macro.capitalize()}*: {actual}{unit} / {goal}{unit}\n`{bar}` {pct}%")
    return "\n\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """👋 *¡Hola! Soy tu bot de nutrición.*

Mandame un *mensaje de voz* o *texto* contando lo que comiste y voy a registrar las calorías y macros automáticamente.

*Comandos disponibles:*
/hoy — Ver resumen del día
/historial — Ver los últimos 7 días
/reset — Reiniciar el día actual
/ayuda — Ver esta ayuda

*Ejemplos de lo que podés decirme:*
• "Me comí 3 huevos revueltos con aguacate y una tostada"
• "Almorcé pechuga de pollo con ensalada"
• "Tomé un batido de proteínas con banana"

¡Empezá contándome qué comiste hoy! 🥗"""
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    today_data = get_user_today(data, update.effective_user.id)
    
    if not today_data["comidas"]:
        await update.message.reply_text("📭 Todavía no registraste nada hoy. ¡Mandame un audio o texto con lo que comiste!")
        return
    
    comidas_text = "\n".join([f"• {c['descripcion']} — {c['calorias']} kcal, {c['proteinas']}g prot" for c in today_data["comidas"]])
    progress = format_progress(today_data["totales"])
    
    msg = f"""📊 *Resumen de hoy — {get_today_key()}*

*Lo que registraste:*
{comidas_text}

*Progreso hacia tus metas:*

{progress}"""
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    
    if uid not in data or not data[uid]:
        await update.message.reply_text("📭 No tenés historial todavía.")
        return
    
    days = sorted(data[uid].keys(), reverse=True)[:7]
    lines = []
    for day in days:
        d = data[uid][day]
        t = d["totales"]
        prot_pct = int((t["proteinas"] / DAILY_GOALS["proteinas"]) * 100)
        cal_pct = int((t["calorias"] / DAILY_GOALS["calorias"]) * 100)
        status = "✅" if prot_pct >= 80 and cal_pct <= 110 else "⚠️"
        lines.append(f"{status} *{day}*: {t['calorias']} kcal | {t['proteinas']}g prot ({prot_pct}%)")
    
    msg = "*📅 Últimos 7 días:*\n\n" + "\n".join(lines)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    today = get_today_key()
    if uid in data and today in data[uid]:
        data[uid][today] = {"comidas": [], "totales": {"calorias": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}
        save_data(data)
    await update.message.reply_text("🔄 Día reiniciado. Empezá de cero.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await process_food_entry(update, context, text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Escuchando tu audio...")
    
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        
        await file.download_to_drive(tmp_path)
        
        transcription = await transcribe_audio_with_claude(tmp_path)
        os.unlink(tmp_path)
        
        await update.message.reply_text(f"📝 *Escuché:* _{transcription}_", parse_mode="Markdown")
        await process_food_entry(update, context, transcription)
        
    except Exception as e:
        logger.error(f"Error procesando audio: {e}")
        await update.message.reply_text("❌ No pude procesar el audio. Intentá escribir lo que comiste.")

async def process_food_entry(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    await update.message.reply_text("🔍 Analizando...")
    
    try:
        result = analyze_food_with_claude(text)
        
        if "error" in result:
            await update.message.reply_text(f"🤔 {result['error']}\n\nContame qué comiste con más detalle.")
            return
        
        data = load_data()
        today_data = get_user_today(data, update.effective_user.id)
        
        today_data["comidas"].append(result)
        for macro in ["calorias", "proteinas", "carbohidratos", "grasas"]:
            today_data["totales"][macro] += result[macro]
        
        save_data(data)
        
        t = today_data["totales"]
        cal_restantes = DAILY_GOALS["calorias"] - t["calorias"]
        prot_restantes = DAILY_GOALS["proteinas"] - t["proteinas"]
        
        cal_status = "✅" if cal_restantes >= 0 else "⚠️ Pasaste el límite"
        prot_status = "✅" if prot_restantes <= 0 else f"Faltan {prot_restantes}g"
        
        msg = f"""✅ *Registrado: {result['descripcion']}*

🔥 {result['calorias']} kcal | 💪 {result['proteinas']}g prot | 🌾 {result['carbohidratos']}g carbs | 🫒 {result['grasas']}g grasas

_{result['comentario']}_

*Acumulado hoy:*
🔥 {t['calorias']} / {DAILY_GOALS['calorias']} kcal {cal_status}
💪 {t['proteinas']} / {DAILY_GOALS['proteinas']}g proteína — {prot_status}

Usá /hoy para ver el resumen completo."""
        
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error analizando comida: {e}")
        await update.message.reply_text("❌ Hubo un error analizando tu comida. Intentá de nuevo.")

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hoy", hoy))
    app.add_handler(CommandHandler("historial", historial))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

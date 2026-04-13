import os
import json
import logging
import traceback
from datetime import datetime, date, timedelta
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
from pymongo import MongoClient
from openai import OpenAI
from achievements import check_new_achievements, get_user_stats, LOGROS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MONGODB_URL = os.environ["MONGODB_URL"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
mongo = MongoClient(MONGODB_URL)
db = mongo["nutrition-bot"]
collection = db["registros"]
logros_col = db["logros"]
conversaciones_col = db["conversaciones"]

ARG_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

DAILY_GOALS = {"calorias": 1900, "proteinas": 160, "carbohidratos": 160, "grasas": 65}

SISTEMA = """Sos el coach personal de Agustín Méndez, 83kg, 1.73m, con rotura de LCA derecho en tratamiento conservador.

Su objetivo: bajar a ~75kg con abdominales marcados, haciendo full body 3 veces por semana en el gym.

Su plan nutricional:
- Meta diaria: 1900 kcal, 160g proteína, 160g carbohidratos, 65g grasas
- Desayuno/almuerzo: 3-5 huevos, aguacate, tostada integral, tomate
- Batido whey (25g proteína) durante el trabajo
- Cena: 350g pollo/merluza/carne magra + ensalada
- Permitido: pizza 1 vez/semana, hamburguesa sin papas 1 vez/semana
- Suplementos: creatina 5g/día, omega 3 2 caps/día, colágeno 10-15g en ayunas con vitamina C, whey proteína

Su plan de entrenamiento (full body 3 días/semana, sin carga axial en rodilla derecha):
- Día A: Press banca plano, Jalón ancho, Elevaciones laterales, Curl EZ, Pushdown polea, Crunch máquina, Curl femoral acostado, Abducción cadera
- Día B: Press inclinado mancuernas, Remo pecho apoyado, Pájaros polea, Curl concentrado, Extensión cabeza mancuerna, Plancha lateral, Prensa rango corto, Curl femoral acostado
- Día C: Cable crossover polea baja, Jalón neutro cerrado, Press militar sentado, Curl martillo, Pushdown cuerda, Rueda abdominal, Elevación piernas barra, Curl femoral sentado, Abducción cadera

Restricciones por LCA: sin sentadillas, sin estocadas, sin peso muerto, sin cardio de impacto, sin pivotes.

Tu personalidad como coach:
- Hablás en español rioplatense, tuteo
- Mezclás motivación real con humor y bardeo con cariño
- Si come bien: lo felicitás con energía
- Si se manda una cagada con la comida: lo bardeás con amor pero lo motivás a seguir
- Si entrena: lo felicitás como si hubiera ganado un mundial
- Sos directo, honesto, no le das la razón en todo
- Usás emojis con moderación
- Respondés preguntas sobre nutrición, ejercicios, suplementos con precisión

CRÍTICO - Extracción de datos:
Al final de CADA respuesta donde el usuario mencione comida o entrenamiento, agregá un bloque JSON oculto así:
<datos>{"tipo": "comida", "descripcion": "...", "calorias": N, "proteinas": N, "carbohidratos": N, "grasas": N}</datos>
o
<datos>{"tipo": "entrenamiento", "descripcion": "..."}</datos>
o
<datos>{"tipo": "ninguno"}</datos>

Si no hay comida ni entrenamiento que registrar, poné <datos>{"tipo": "ninguno"}</datos>
Usá estimaciones realistas para porciones argentinas típicas.
NUNCA muestres el bloque <datos> al usuario, es solo para el sistema."""

def get_today_arg():
    return datetime.now(ARG_TZ).strftime("%Y-%m-%d")

def get_user_today(user_id):
    today = get_today_arg()
    uid = str(user_id)
    doc = collection.find_one({"user_id": uid, "fecha": today})
    if not doc:
        doc = {
            "user_id": uid,
            "fecha": today,
            "comidas": [],
            "entrenamientos": [],
            "totales": {"calorias": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}
        }
        collection.insert_one(doc)
        doc = collection.find_one({"user_id": uid, "fecha": today})
    return doc

def save_user_today(user_id, doc):
    today = get_today_arg()
    uid = str(user_id)
    collection.update_one(
        {"user_id": uid, "fecha": today},
        {"$set": {
            "comidas": doc["comidas"],
            "entrenamientos": doc["entrenamientos"],
            "totales": doc["totales"]
        }}
    )

def get_conversation_history(user_id):
    today = get_today_arg()
    uid = str(user_id)
    doc = conversaciones_col.find_one({"user_id": uid, "fecha": today})
    if doc:
        return doc.get("mensajes", [])
    return []

def save_conversation_history(user_id, history):
    today = get_today_arg()
    uid = str(user_id)
    # Mantener solo los últimos 20 mensajes para no gastar tokens
    history = history[-20:]
    conversaciones_col.update_one(
        {"user_id": uid, "fecha": today},
        {"$set": {"mensajes": history}},
        upsert=True
    )

def build_context(user_id):
    doc = get_user_today(user_id)
    t = doc["totales"]
    
    context_parts = [f"📅 Hoy es {get_today_arg()}"]
    
    if doc["comidas"]:
        context_parts.append(f"Comidas registradas hoy: {', '.join([c['descripcion'] for c in doc['comidas']])}")
        context_parts.append(f"Acumulado: {t['calorias']} kcal / {t['proteinas']}g prot / {t['carbohidratos']}g carbs / {t['grasas']}g grasas")
        cal_rest = DAILY_GOALS['calorias'] - t['calorias']
        prot_rest = DAILY_GOALS['proteinas'] - t['proteinas']
        context_parts.append(f"Le quedan: {cal_rest} kcal y {prot_rest}g proteína para la meta")
    else:
        context_parts.append("No registró comidas hoy todavía")
    
    if doc["entrenamientos"]:
        context_parts.append(f"Entrenó hoy: {doc['entrenamientos'][0]['descripcion']}")
    else:
        context_parts.append("No registró entrenamiento hoy")
    
    uid = str(user_id)
    _, stats = check_new_achievements(collection, uid, logros_col)
    context_parts.append(f"Racha actual: {stats['racha_actual']} días. Total entrenamientos: {stats['total_entrenos']}")
    
    return "\n".join(context_parts)

def extract_and_clean(text):
    import re
    pattern = r'<datos>(.*?)</datos>'
    match = re.search(pattern, text, re.DOTALL)
    datos = None
    if match:
        try:
            datos = json.loads(match.group(1).strip())
        except:
            datos = {"tipo": "ninguno"}
        text = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    return text, datos

def format_progress_inline(totales):
    t = totales
    cal_pct = min(int((t['calorias'] / DAILY_GOALS['calorias']) * 100), 100)
    prot_pct = min(int((t['proteinas'] / DAILY_GOALS['proteinas']) * 100), 100)
    return f"🔥 {t['calorias']}/{DAILY_GOALS['calorias']} kcal ({cal_pct}%) | 💪 {t['proteinas']}/{DAILY_GOALS['proteinas']}g prot ({prot_pct}%)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """👋 *¡Hola Agustín! Soy tu coach personal.*

Hablame como si fuera una persona. Contame qué comiste, si entrenaste, cómo te sentís, preguntame lo que quieras sobre el plan.

*Comandos rápidos:*
/hoy — Resumen del día
/historial — Últimos 7 días  
/logros — Tus logros y estadísticas
/entrenamiento — Ejercicios de hoy
/entrenamiento A · B · C — Ver un día específico
/ejercicio [nombre] — Cómo hacer un ejercicio
/semana — Semana completa
/reset — Reiniciar el día"""
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = get_user_today(update.effective_user.id)
    lines = [f"📊 *Resumen de hoy — {get_today_arg()}*\n"]
    if doc["comidas"]:
        lines.append("*Comidas:*")
        for c in doc["comidas"]:
            lines.append(f"• {c['descripcion']} — {c['calorias']} kcal, {c['proteinas']}g prot")
        lines.append("")
        t = doc["totales"]
        cal_pct = min(int((t['calorias'] / DAILY_GOALS['calorias']) * 100), 100)
        prot_pct = min(int((t['proteinas'] / DAILY_GOALS['proteinas']) * 100), 100)
        cal_bar = "█" * int(cal_pct/10) + "░" * (10 - int(cal_pct/10))
        prot_bar = "█" * int(prot_pct/10) + "░" * (10 - int(prot_pct/10))
        lines.append("*Progreso:*")
        lines.append(f"🔥 {t['calorias']}/{DAILY_GOALS['calorias']} kcal\n`{cal_bar}` {cal_pct}%")
        lines.append(f"💪 {t['proteinas']}/{DAILY_GOALS['proteinas']}g prot\n`{prot_bar}` {prot_pct}%")
    else:
        lines.append("_Sin comidas registradas._")
    if doc["entrenamientos"]:
        lines.append(f"\n🏋️ *Entrenó:* {doc['entrenamientos'][0]['descripcion']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    docs = list(collection.find({"user_id": uid}).sort("fecha", -1).limit(7))
    if not docs:
        await update.message.reply_text("📭 No tenés historial todavía.")
        return
    lines = ["*📅 Últimos 7 días:*\n"]
    for d in docs:
        t = d["totales"]
        prot_pct = int((t["proteinas"] / DAILY_GOALS["proteinas"]) * 100)
        cal_pct = int((t["calorias"] / DAILY_GOALS["calorias"]) * 100)
        status = "✅" if prot_pct >= 80 and cal_pct <= 110 else "⚠️"
        entreno = "🏋️" if d.get("entrenamientos") else "😴"
        lines.append(f"{status}{entreno} *{d['fecha']}*: {t['calorias']} kcal | {t['proteinas']}g prot ({prot_pct}%)")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def logros(update, context):
    uid = str(update.effective_user.id)
    _, stats = check_new_achievements(collection, uid, logros_col)
    earned_ids = set(l["id"] for l in logros_col.find({"user_id": uid}))
    lines = ["🏅 *Tus logros*\n"]
    lines.append(f"🔥 Racha actual: *{stats['racha_actual']} días*")
    lines.append(f"🏋️ Total entrenamientos: *{stats['total_entrenos']}*")
    lines.append(f"💪 Días con proteína cumplida: *{stats['dias_proteina_ok']}*")
    lines.append(f"📉 Días en déficit: *{stats['dias_calorias_ok']}*\n")
    lines.append("*Logros:*")
    for l in LOGROS:
        if l["id"] in earned_ids:
            lines.append(f"✅ {l['emoji']} *{l['nombre']}* — _{l['desc']}_")
        else:
            lines.append(f"🔒 ??? — _{l['desc']}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    today = get_today_arg()
    collection.update_one(
        {"user_id": uid, "fecha": today},
        {"$set": {"comidas": [], "entrenamientos": [], "totales": {"calorias": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}}
    )
    conversaciones_col.delete_one({"user_id": uid, "fecha": today})
    await update.message.reply_text("🔄 Día reiniciado.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import tempfile
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)
        with open(tmp_path, "rb") as f:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es"
            )
        os.unlink(tmp_path)
        transcription = transcript.text
        await update.message.reply_text(f"🎙️ _{transcription}_", parse_mode="Markdown")
        await process_message(update, context, transcription)
    except Exception as e:
        logger.error(f"Error audio: {traceback.format_exc()}")
        await update.message.reply_text("❌ No pude procesar el audio. Escribime.")

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    uid = str(user_id)

    try:
        history = get_conversation_history(user_id)
        context_today = build_context(user_id)
        
        system_with_context = SISTEMA + f"\n\nCONTEXTO ACTUAL DEL DÍA:\n{context_today}"
        
        history.append({"role": "user", "content": text})
        
        response = client_ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system_with_context,
            messages=history
        )
        
        raw_response = response.content[0].text
        clean_response, datos = extract_and_clean(raw_response)
        
        history.append({"role": "assistant", "content": raw_response})
        save_conversation_history(user_id, history)
        
        await update.message.reply_text(clean_response, parse_mode="Markdown")
        
        if datos and datos.get("tipo") == "comida":
            doc = get_user_today(user_id)
            doc["comidas"].append(datos)
            for macro in ["calorias", "proteinas", "carbohidratos", "grasas"]:
                doc["totales"][macro] += datos.get(macro, 0)
            save_user_today(user_id, doc)
            
            t = doc["totales"]
            progress = format_progress_inline(t)
            await update.message.reply_text(f"📊 {progress}", parse_mode="Markdown")
            
            new_achievements, _ = check_new_achievements(collection, uid, logros_col)
            for logro in new_achievements:
                await update.message.reply_text(
                    f"🏅 *LOGRO: {logro['nombre']}* {logro['emoji']}\n_{logro['desc']}_",
                    parse_mode="Markdown"
                )

        elif datos and datos.get("tipo") == "entrenamiento":
            doc = get_user_today(user_id)
            if not doc["entrenamientos"]:
                doc["entrenamientos"].append({"descripcion": datos.get("descripcion", "Entrenamiento")})
                save_user_today(user_id, doc)
            
            new_achievements, stats = check_new_achievements(collection, uid, logros_col)
            
            if stats["racha_actual"] > 1:
                await update.message.reply_text(f"🔥 Racha: *{stats['racha_actual']} días* | Total: *{stats['total_entrenos']} entrenamientos*", parse_mode="Markdown")
            
            for logro in new_achievements:
                await update.message.reply_text(
                    f"🏅 *LOGRO: {logro['nombre']}* {logro['emoji']}\n_{logro['desc']}_",
                    parse_mode="Markdown"
                )

    except Exception as e:
        logger.error(f"Error: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, context, update.message.text)

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

from training_module import PLAN, SEMANA, get_dia_hoy

async def entrenamiento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].upper() in ["A", "B", "C"]:
        dia_key = args[0].upper()
    else:
        dia_key = get_dia_hoy()
    if not dia_key:
        await update.message.reply_text("💤 *Hoy es día de descanso.*\n\n/entrenamiento A · B · C para ver un día específico.", parse_mode="Markdown")
        return
    dia = PLAN[dia_key]
    lines = [f"🏋️ *{dia['nombre']}*\n_{dia['enfasis']}_\n"]
    for g in dia["grupos"]:
        lines.append(f"*{g['grupo']}*")
        for ex in g["ejercicios"]:
            lines.append(f"• {ex['nombre']} — {ex['series']}\n  _{ex['porcion']}_")
        lines.append("")
    lines.append("Usá /ejercicio nombre para ver cómo se hace.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def ejercicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Ejemplo: /ejercicio curl martillo")
        return
    query = " ".join(context.args).lower()
    encontrado = None
    for dia in PLAN.values():
        for g in dia["grupos"]:
            for ex in g["ejercicios"]:
                if query in ex["nombre"].lower():
                    encontrado = ex
                    break
    if not encontrado:
        await update.message.reply_text(f"❌ No encontré *{query}*.", parse_mode="Markdown")
        return
    msg = f"💪 *{encontrado['nombre']}*\n_{encontrado['porcion']}_\n\n*Series:* {encontrado['series']}\n\n*Cómo:*\n{encontrado['como']}\n\n*Tip:*\n_{encontrado['tip']}_"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def semana_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    hoy_idx = datetime.now(ARG_TZ).weekday()
    lines = ["📅 *Semana de entrenamiento:*\n"]
    for i, nombre in enumerate(dias_nombres):
        dia_key = SEMANA.get(i)
        marcador = " ◀ hoy" if i == hoy_idx else ""
        if dia_key:
            lines.append(f"*{nombre}* — Día {dia_key}{marcador}\n_{PLAN[dia_key]['enfasis']}_")
        else:
            lines.append(f"*{nombre}* — Descanso 💤{marcador}")
        lines.append("")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hoy", hoy))
    app.add_handler(CommandHandler("historial", historial))
    app.add_handler(CommandHandler("logros", logros))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("entrenamiento", entrenamiento))
    app.add_handler(CommandHandler("ejercicio", ejercicio))
    app.add_handler(CommandHandler("semana", semana_cmd))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Bot iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

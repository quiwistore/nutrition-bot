import os
import json
import logging
import tempfile
from datetime import datetime, date
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
from pymongo import MongoClient
from achievements import check_new_achievements, get_user_stats, LOGROS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MONGODB_URL = os.environ["MONGODB_URL"]

client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
mongo = MongoClient(MONGODB_URL)
db = mongo["nutrition-bot"]
collection = db["registros"]

ARG_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

DAILY_GOALS = {
    "calorias": 1900,
    "proteinas": 160,
    "carbohidratos": 160,
    "grasas": 65
}

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

def analyze_with_claude(text):
    prompt = f"""Sos un asistente de nutrición y entrenamiento. El usuario te manda este mensaje: "{text}"

IMPORTANTE: Cualquier mensaje que indique que el usuario hizo ejercicio o fue al gym DEBE clasificarse como ENTRENAMIENTO, incluso si es muy corto o informal. Ejemplos de ENTRENAMIENTO: "ya entrené", "fui al gym", "listo entrené", "hice el día A", "terminé el entrenamiento", "entrené hoy", "fui a entrenar", "hice la rutina", "ya fui", "entrené".

Clasificá el mensaje en:
1. COMIDA - el usuario describe algo que comió o tomó
2. ENTRENAMIENTO - cualquier referencia a haber hecho ejercicio, gym, rutina, entreno
3. OTRO - consulta, saludo, o cualquier otra cosa

Respondé SOLO con un JSON válido sin texto extra:

Si es COMIDA:
{{"tipo": "comida", "descripcion": "descripción corta", "calorias": número, "proteinas": número, "carbohidratos": número, "grasas": número, "comentario": "comentario breve en español rioplatense"}}

Si es ENTRENAMIENTO:
{{"tipo": "entrenamiento", "descripcion": "qué entrenamiento hizo", "comentario": "comentario motivador breve en español rioplatense"}}

Si es OTRO:
{{"tipo": "otro", "respuesta": "respuesta breve y amigable en español rioplatense"}}

Para el campo "comentario" en comidas SÉ MUY HONESTO y divertido. Ejemplos del tono que buscamos:
- Si comió bien: "Eso es lo que es, proteína al palo. Seguila así."
- Si comió medialunas/alfajores/facturas: "Bah, las medialunas... clásico. Disfrutaste, pero no te olvides que eso no te acerca a los abs."
- Si comió pizza: "La pizza semanal, bienvenida. Contala como el cheat del día y mañana volvemos al plan."
- Si comió pollo con ensalada: "Eso sí que es comer como un campeón. Sos un monstruo."
- Si se pasó de calorías: "Hoy te fuiste de mambo con las calorías. Mañana la revancha, no drama."
- Si cumplió la proteína: "¡Meta de proteína cumplida! Así se construye músculo, no con rezos."
Usá humor rioplatense, bardeo con cariño y motivación real. Máximo 2 oraciones."""

    response = client_ai.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def format_progress(totales):
    lines = []
    items = [
        ("calorias", "🔥", "kcal"),
        ("proteinas", "💪", "g"),
        ("carbohidratos", "🌾", "g"),
        ("grasas", "🫒", "g")
    ]
    for macro, emoji, unit in items:
        actual = totales[macro]
        goal = DAILY_GOALS[macro]
        pct = min(int((actual / goal) * 100), 100)
        bar = "█" * int(pct/10) + "░" * (10 - int(pct/10))
        lines.append(f"{emoji} *{macro.capitalize()}*: {actual}{unit} / {goal}{unit}\n`{bar}` {pct}%")
    return "\n\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """👋 *¡Hola! Soy tu bot de nutrición y entrenamiento.*

Contame lo que comiste o si entrenaste y lo registro automáticamente.

*Comandos:*
/hoy — Resumen del día
/historial — Últimos 7 días
/entrenamiento — Ejercicios de hoy
/entrenamiento A · B · C — Ver un día específico
/ejercicio [nombre] — Cómo hacer un ejercicio
/semana — Semana completa
/reset — Reiniciar el día
/logros — Ver tus logros y estadísticas
/ayuda — Ver esta ayuda

*Ejemplos:*
• "Comí 3 huevos con aguacate y una tostada"
• "Hice el entrenamiento de hoy"
• "Tomé un café con leche"
• "Fui al gym e hice el día B" """
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = get_user_today(update.effective_user.id)

    lines = [f"📊 *Resumen de hoy — {get_today_arg()}*\n"]

    if doc["comidas"]:
        lines.append("*Comidas registradas:*")
        for c in doc["comidas"]:
            lines.append(f"• {c['descripcion']} — {c['calorias']} kcal, {c['proteinas']}g prot")
        lines.append("")
    else:
        lines.append("_Sin comidas registradas todavía._\n")

    if doc["entrenamientos"]:
        lines.append("*Entrenamientos:*")
        for e in doc["entrenamientos"]:
            lines.append(f"• {e['descripcion']}")
        lines.append("")

    if doc["comidas"]:
        lines.append("*Progreso macros:*\n")
        lines.append(format_progress(doc["totales"]))

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

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    today = get_today_arg()
    collection.update_one(
        {"user_id": uid, "fecha": today},
        {"$set": {"comidas": [], "entrenamientos": [], "totales": {"calorias": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}}
    )
    await update.message.reply_text("🔄 Día reiniciado.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Los audios estarán disponibles próximamente.\n\nPor ahora escribí lo que comiste o entrenaste.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text("🔍 Procesando...")

    try:
        result = analyze_with_claude(text)
        doc = get_user_today(update.effective_user.id)

        if result["tipo"] == "comida":
            doc["comidas"].append(result)
            for macro in ["calorias", "proteinas", "carbohidratos", "grasas"]:
                doc["totales"][macro] += result[macro]
            save_user_today(update.effective_user.id, doc)

            t = doc["totales"]
            cal_rest = DAILY_GOALS["calorias"] - t["calorias"]
            prot_rest = DAILY_GOALS["proteinas"] - t["proteinas"]
            cal_status = "✅" if cal_rest >= 0 else f"⚠️ Pasaste por {abs(cal_rest)} kcal"
            prot_status = "✅ Meta cumplida" if prot_rest <= 0 else f"Faltan {prot_rest}g"

            msg = f"""✅ *Registrado: {result['descripcion']}*

🔥 {result['calorias']} kcal | 💪 {result['proteinas']}g | 🌾 {result['carbohidratos']}g | 🫒 {result['grasas']}g

_{result['comentario']}_

*Acumulado hoy:*
🔥 {t['calorias']} / {DAILY_GOALS['calorias']} kcal — {cal_status}
💪 {t['proteinas']} / {DAILY_GOALS['proteinas']}g proteína — {prot_status}

Usá /hoy para el resumen completo."""
            await update.message.reply_text(msg, parse_mode="Markdown")

        elif result["tipo"] == "entrenamiento":
            doc["entrenamientos"].append({"descripcion": result["descripcion"]})
            save_user_today(update.effective_user.id, doc)
            
            uid = str(update.effective_user.id)
            new_achievements, stats = check_new_achievements(collection, uid, logros_col)
            
            racha = stats["racha_actual"]
            racha_txt = f"\n🔥 *Racha: {racha} día(s) consecutivo(s)*" if racha > 1 else ""
            total_txt = f"\n💪 Total acumulado: *{stats['total_entrenos']} entrenos*"
            
            msg = f"""🏋️ *Entrenamiento registrado*\n\n{result['descripcion']}\n\n_{result['comentario']}_\n{racha_txt}{total_txt}\n\nUsá /hoy para ver el resumen del día."""
            await update.message.reply_text(msg, parse_mode="Markdown")
            
            for logro in new_achievements:
                await update.message.reply_text(
                    f"🏅 *LOGRO DESBLOQUEADO: {logro['nombre']}* {logro['emoji']}\n\n_{logro['desc']}_\n\n¡La estás rompiendo, Agustín!",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(result["respuesta"])

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Hubo un error. Intentá de nuevo.")


async def logros(update, context):
    uid = str(update.effective_user.id)
    _, stats = check_new_achievements(collection, uid, logros_col)
    earned = list(logros_col.find({"user_id": uid}))
    earned_ids = set(l["id"] for l in earned)
    
    lines = ["🏅 *Tus logros*\n"]
    
    lines.append(f"🔥 Racha actual: *{stats['racha_actual']} días*")
    lines.append(f"🏋️ Total entrenamientos: *{stats['total_entrenos']}*")
    lines.append(f"💪 Días con proteína cumplida: *{stats['dias_proteina_ok']}*")
    lines.append(f"📉 Días en déficit calórico: *{stats['dias_calorias_ok']}*\n")
    
    lines.append("*Logros desbloqueados:*")
    from achievements import LOGROS
    for l in LOGROS:
        if l["id"] in earned_ids:
            lines.append(f"✅ {l['emoji']} {l['nombre']} — _{l['desc']}_")
        else:
            lines.append(f"🔒 ??? — _{l['desc']}_")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

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
        await update.message.reply_text("💤 *Hoy es día de descanso.*\n\nPodés consultar un día específico con:\n/entrenamiento A\n/entrenamiento B\n/entrenamiento C", parse_mode="Markdown")
        return

    dia = PLAN[dia_key]
    lines = [f"🏋️ *{dia['nombre']}*\n_{dia['enfasis']}_\n"]
    for g in dia["grupos"]:
        lines.append(f"*{g['grupo']}*")
        for ex in g["ejercicios"]:
            lines.append(f"• {ex['nombre']} — {ex['series']}\n  _{ex['porcion']}_")
        lines.append("")
    lines.append("Usá /ejercicio nombre para ver cómo se hace cualquier ejercicio.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def ejercicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Escribí el nombre del ejercicio.\nEjemplo: /ejercicio curl martillo")
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
        await update.message.reply_text(f"❌ No encontré *{query}*.\n\nUsá /entrenamiento para ver todos los ejercicios.", parse_mode="Markdown")
        return
    msg = f"💪 *{encontrado['nombre']}*\n_{encontrado['porcion']}_\n\n*Series:* {encontrado['series']}\n\n*Cómo se hace:*\n{encontrado['como']}\n\n*Tip:*\n_{encontrado['tip']}_"
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
    lines.append("Usá /entrenamiento para ver los ejercicios de hoy.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hoy", hoy))
    app.add_handler(CommandHandler("historial", historial))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("logros", logros))
    app.add_handler(CommandHandler("entrenamiento", entrenamiento))
    app.add_handler(CommandHandler("ejercicio", ejercicio))
    app.add_handler(CommandHandler("semana", semana_cmd))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Bot iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

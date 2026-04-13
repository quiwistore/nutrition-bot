from datetime import datetime, timedelta
import pytz

ARG_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

LOGROS = [
    {"id": "primer_entreno", "nombre": "Primer paso", "emoji": "👟", "desc": "Primer entrenamiento registrado"},
    {"id": "entrenos_5", "nombre": "Arrancaste en serio", "emoji": "💪", "desc": "5 entrenamientos completados"},
    {"id": "entrenos_10", "nombre": "Doble dígito", "emoji": "🔥", "desc": "10 entrenamientos completados"},
    {"id": "entrenos_20", "nombre": "Ya sos un atleta", "emoji": "🏆", "desc": "20 entrenamientos completados"},
    {"id": "entrenos_30", "nombre": "Un mes de guerra", "emoji": "🥇", "desc": "30 entrenamientos completados"},
    {"id": "entrenos_50", "nombre": "Monstruo", "emoji": "👹", "desc": "50 entrenamientos completados"},
    {"id": "racha_3", "nombre": "3 días seguidos", "emoji": "⚡", "desc": "3 días consecutivos entrenando"},
    {"id": "racha_7", "nombre": "Semana perfecta", "emoji": "🌟", "desc": "7 días consecutivos entrenando"},
    {"id": "racha_14", "nombre": "Dos semanas sin parar", "emoji": "🚀", "desc": "14 días consecutivos entrenando"},
    {"id": "proteina_goal", "nombre": "Proteína al tope", "emoji": "🥩", "desc": "Primer día cumpliendo meta de proteína"},
    {"id": "proteina_7dias", "nombre": "Una semana proteico", "emoji": "💯", "desc": "7 días cumpliendo meta de proteína"},
    {"id": "calorias_ok_7dias", "nombre": "Semana en déficit", "emoji": "📉", "desc": "7 días dentro del objetivo calórico"},
    {"id": "sin_junk_semana", "nombre": "Semana santa", "emoji": "😇", "desc": "Una semana sin registrar comida chatarra"},
]

def get_user_stats(collection, uid):
    docs = list(collection.find({"user_id": uid}).sort("fecha", 1))
    
    total_entrenos = sum(1 for d in docs if d.get("entrenamientos"))
    
    racha_actual = 0
    racha_max = 0
    fechas_entreno = sorted([d["fecha"] for d in docs if d.get("entrenamientos")])
    
    if fechas_entreno:
        racha = 1
        for i in range(1, len(fechas_entreno)):
            d1 = datetime.strptime(fechas_entreno[i-1], "%Y-%m-%d")
            d2 = datetime.strptime(fechas_entreno[i], "%Y-%m-%d")
            if (d2 - d1).days == 1:
                racha += 1
            else:
                racha_max = max(racha_max, racha)
                racha = 1
        racha_max = max(racha_max, racha)
        
        hoy = datetime.now(ARG_TZ).strftime("%Y-%m-%d")
        ayer = (datetime.now(ARG_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        if fechas_entreno[-1] in [hoy, ayer]:
            racha_actual = 1
            for i in range(len(fechas_entreno)-2, -1, -1):
                d1 = datetime.strptime(fechas_entreno[i], "%Y-%m-%d")
                d2 = datetime.strptime(fechas_entreno[i+1], "%Y-%m-%d")
                if (d2 - d1).days == 1:
                    racha_actual += 1
                else:
                    break

    dias_proteina_ok = sum(1 for d in docs if d["totales"]["proteinas"] >= 140)
    dias_calorias_ok = sum(1 for d in docs if 0 < d["totales"]["calorias"] <= 2100)
    
    return {
        "total_entrenos": total_entrenos,
        "racha_actual": racha_actual,
        "racha_max": racha_max,
        "dias_proteina_ok": dias_proteina_ok,
        "dias_calorias_ok": dias_calorias_ok,
        "total_dias": len(docs),
    }

def check_new_achievements(collection, uid, logros_col):
    stats = get_user_stats(collection, uid)
    existing = set(l["id"] for l in logros_col.find({"user_id": uid}))
    new_ones = []

    checks = [
        ("primer_entreno", stats["total_entrenos"] >= 1),
        ("entrenos_5", stats["total_entrenos"] >= 5),
        ("entrenos_10", stats["total_entrenos"] >= 10),
        ("entrenos_20", stats["total_entrenos"] >= 20),
        ("entrenos_30", stats["total_entrenos"] >= 30),
        ("entrenos_50", stats["total_entrenos"] >= 50),
        ("racha_3", stats["racha_actual"] >= 3),
        ("racha_7", stats["racha_actual"] >= 7),
        ("racha_14", stats["racha_actual"] >= 14),
        ("proteina_goal", stats["dias_proteina_ok"] >= 1),
        ("proteina_7dias", stats["dias_proteina_ok"] >= 7),
        ("calorias_ok_7dias", stats["dias_calorias_ok"] >= 7),
    ]

    for logro_id, condition in checks:
        if condition and logro_id not in existing:
            logros_col.insert_one({"user_id": uid, "id": logro_id, "fecha": datetime.now(ARG_TZ).strftime("%Y-%m-%d")})
            logro_data = next((l for l in LOGROS if l["id"] == logro_id), None)
            if logro_data:
                new_ones.append(logro_data)

    return new_ones, stats

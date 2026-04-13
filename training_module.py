from datetime import date

PLAN = {
    "A": {
        "nombre": "Día A — Pecho medio · Bíceps masa · Dorsal ancho · Hombro lateral · Core recto",
        "enfasis": "Fuerza — series pesadas",
        "grupos": [
            {"grupo": "Pecho", "ejercicios": [{"nombre": "Press de banca plano con barra", "series": "4×8–10", "porcion": "Pecho medio", "como": "Acostado en banco plano, agarre a anchura de hombros. Bajá la barra controlado hasta rozar el pecho, codos a 45°. Empujá explosivo. Espalda levemente arqueada, pies en el suelo.", "tip": "Bajá en 3 segundos, subí en 1. El músculo crece más en la fase de bajada."}]},
            {"grupo": "Espalda", "ejercicios": [{"nombre": "Jalón al pecho agarre ancho", "series": "4×10", "porcion": "Dorsal ancho — forma en V", "como": "Sentado, agarre prono ancho. Jalá la barra hasta el pecho llevando los codos hacia abajo y atrás. No te eches más de 15° hacia atrás.", "tip": "Pensá en meter los codos en los bolsillos. Eso aísla el dorsal."}]},
            {"grupo": "Hombro", "ejercicios": [{"nombre": "Elevaciones laterales con mancuernas", "series": "4×15", "porcion": "Deltoides lateral", "como": "De pie o sentado. Subí hasta la altura del hombro con el meñique levemente más alto que el pulgar. Bajá controlado.", "tip": "Peso ligero, muchas reps. El deltoides lateral responde mejor al volumen alto."}]},
            {"grupo": "Bíceps", "ejercicios": [{"nombre": "Curl con barra EZ", "series": "3×10", "porcion": "Masa general — cabeza larga y corta", "como": "De pie, agarre semisupino en la barra EZ. Codos fijos al costado. Subí hasta el hombro, bajá completamente. No balancees la cadera.", "tip": "La barra EZ reduce estrés en la muñeca frente a la barra recta."}]},
            {"grupo": "Tríceps", "ejercicios": [{"nombre": "Pushdown en polea con barra recta", "series": "3×12", "porcion": "Cabeza lateral", "como": "De pie frente a la polea alta. Codos pegados al cuerpo, empujá hacia abajo extendiendo completamente. No muevas los hombros.", "tip": "Agarre prono activa más la cabeza lateral. Controlá la subida."}]},
            {"grupo": "Core", "ejercicios": [{"nombre": "Crunch en máquina o polea", "series": "3×15", "porcion": "Recto abdominal", "como": "En la máquina o de rodillas frente a la polea alta. Flexioná el tronco contrayendo el abdomen. Mantenélo 1 seg contraído.", "tip": "La resistencia externa permite progresar con carga."}]},
            {"grupo": "Pierna segura LCA", "ejercicios": [{"nombre": "Curl femoral acostado en máquina", "series": "4×12", "porcion": "Isquiotibiales — terapéutico para LCA", "como": "Acostado boca abajo. Talones hacia los glúteos. Bajá en 3 segundos controlado.", "tip": "Fortalecer isquiotibiales es parte del tratamiento conservador del LCA."}, {"nombre": "Abducción de cadera en máquina", "series": "3×15", "porcion": "Glúteo medio — estabilidad de rodilla", "como": "Sentado en la máquina. Abrí las piernas contra la resistencia, mantenélo 1 seg, volvé controlado.", "tip": "El glúteo medio estabiliza lateralmente la rodilla y reduce estrés en el LCA."}]}
        ]
    },
    "B": {
        "nombre": "Día B — Pecho superior · Bíceps pico · Dorsal grosor · Hombro posterior · Core oblicuos",
        "enfasis": "Hipertrofia — series moderadas",
        "grupos": [
            {"grupo": "Pecho", "ejercicios": [{"nombre": "Press inclinado con mancuernas", "series": "4×10–12", "porcion": "Pecho superior", "como": "Banco a 30–35°. Mancuernas a la altura del pecho, palmas hacia adelante. Empujá hacia arriba y levemente al centro. No bloqueés los codos.", "tip": "30° activa más pecho superior que 45°. A mayor ángulo, más hombro y menos pecho."}]},
            {"grupo": "Espalda", "ejercicios": [{"nombre": "Remo en máquina con pecho apoyado", "series": "4×10", "porcion": "Dorsal grosor + romboides", "como": "Pecho apoyado en el respaldo inclinado. Jalá los mangos hacia atrás llevando los codos bien detrás del cuerpo. Apretá los omóplatos 1 seg.", "tip": "Sin carga en el tren inferior. Podés subir el peso con confianza."}]},
            {"grupo": "Hombro", "ejercicios": [{"nombre": "Pájaros en polea baja o mancuernas", "series": "4×15", "porcion": "Deltoides posterior", "como": "Inclinado al frente o en peck deck al revés. Abrí los brazos hacia atrás como alas con codos levemente flexionados. Controlá la vuelta.", "tip": "El hombro posterior da redondez visual y mejora la postura."}]},
            {"grupo": "Bíceps", "ejercicios": [{"nombre": "Curl concentrado en banco", "series": "3×12", "porcion": "Pico del bíceps — cabeza larga", "como": "Sentado, codo apoyado en la cara interna del muslo. Curl completo rotando la muñeca hacia afuera al subir. Una mano a la vez.", "tip": "La supinación al final contrae el bíceps al máximo. Es el ejercicio del pico visual."}]},
            {"grupo": "Tríceps", "ejercicios": [{"nombre": "Extensión sobre la cabeza con mancuerna", "series": "3×12", "porcion": "Cabeza larga — la más grande", "como": "Sentado, mancuerna con ambas manos sobre la cabeza. Bajá doblando los codos detrás hasta ~90°, extendé. Codos apuntando al techo.", "tip": "La cabeza larga solo se estira completamente con el brazo elevado."}]},
            {"grupo": "Core", "ejercicios": [{"nombre": "Plancha lateral", "series": "3×40'' cada lado", "porcion": "Oblicuos", "como": "Apoyado en un antebrazo y el costado del pie. Cuerpo recto, cadera arriba.", "tip": "Si la rodilla molesta, apoyala en el suelo en lugar del pie."}]},
            {"grupo": "Pierna segura LCA", "ejercicios": [{"nombre": "Prensa de piernas rango corto", "series": "4×12", "porcion": "Cuádriceps — sin carga axial", "como": "Rango entre 60° y 90° de flexión de rodilla, nunca más profundo. Peso moderado.", "tip": "⚠️ Consultá con tu kinesiólogo si este ejercicio está permitido."}, {"nombre": "Curl femoral acostado en máquina", "series": "4×12", "porcion": "Isquiotibiales", "como": "Acostado boca abajo. Talones hacia los glúteos. Bajá en 3 segundos.", "tip": "Se repite los 3 días porque es el más importante para la rodilla."}]}
        ]
    },
    "C": {
        "nombre": "Día C — Pecho inferior · Bíceps grosor · Trapecio · Hombro anterior · Core profundo",
        "enfasis": "Definición — contracción y volumen",
        "grupos": [
            {"grupo": "Pecho", "ejercicios": [{"nombre": "Cable crossover en polea baja", "series": "4×12–15", "porcion": "Pecho inferior", "como": "Poleas bajas a cada lado. Inclinado al frente, llevá los cables hacia arriba y al centro. Mantenélo 1 seg en la contracción.", "tip": "Peso ligero, máxima contracción. Define la línea inferior del pecho."}]},
            {"grupo": "Espalda", "ejercicios": [{"nombre": "Jalón agarre neutro cerrado", "series": "4×10", "porcion": "Dorsal bajo + trapecio", "como": "Agarre neutro con barra V o mangos paralelos. Jalá hacia el pecho con los codos pegados al cuerpo.", "tip": "El agarre neutro cerrado activa más la parte baja del dorsal que el agarre ancho."}]},
            {"grupo": "Hombro", "ejercicios": [{"nombre": "Press militar con mancuernas sentado", "series": "4×10", "porcion": "Deltoides anterior + completo", "como": "Sentado con respaldo. Mancuernas a la altura de las orejas. Empujá hacia arriba sin bloquear los codos. Bajá hasta la altura del hombro.", "tip": "Sentado con respaldo = cero carga en la rodilla."}]},
            {"grupo": "Bíceps", "ejercicios": [{"nombre": "Curl martillo con mancuernas", "series": "3×12", "porcion": "Braquial + braquiorradial — grosor total del brazo", "como": "Agarre neutro (pulgar arriba). Subí sin rotar la muñeca. Alternado o simultáneo. Codos fijos al cuerpo.", "tip": "El braquial empuja el bíceps hacia arriba visualmente. Da más grosor total al brazo."}]},
            {"grupo": "Tríceps", "ejercicios": [{"nombre": "Pushdown con cuerda en polea", "series": "3×15", "porcion": "Cabeza medial", "como": "Igual que el pushdown pero con cuerda. Al llegar abajo, separás las manos hacia afuera para máxima contracción.", "tip": "La cuerda activa la cabeza medial más que la barra."}]},
            {"grupo": "Core", "ejercicios": [{"nombre": "Rueda abdominal de rodillas", "series": "3×8–12", "porcion": "Transverso + recto abdominal", "como": "De rodillas, rueda al frente con espalda recta. Extendé hasta donde puedas sin hundir la lumbar. Volvé contrayendo el abdomen.", "tip": "Empezá con poco rango. Es el ejercicio más exigente de core."}, {"nombre": "Elevación de piernas colgado en barra", "series": "3×12–15", "porcion": "Abdominales inferiores", "como": "Colgado de la barra. Levantá las piernas hasta 90°. Bajá sin balancear.", "tip": "Sin impacto en la rodilla. Con rodillas dobladas es más fácil para empezar."}]},
            {"grupo": "Pierna segura LCA", "ejercicios": [{"nombre": "Curl femoral sentado en máquina", "series": "4×12", "porcion": "Isquiotibiales — ángulo distinto al acostado", "como": "En la máquina de curl femoral sentado. El ángulo de cadera flexionada estira más la cabeza larga del bíceps femoral.", "tip": "Alternás con la versión acostada para trabajar desde dos ángulos."}, {"nombre": "Abducción de cadera en máquina", "series": "3×15", "porcion": "Glúteo medio", "como": "Sentado en la máquina. Abrí las piernas contra la resistencia, mantenélo 1 seg, volvé controlado.", "tip": "Fortalece el estabilizador lateral de la rodilla."}]}
        ]
    }
}

SEMANA = {0: "A", 1: None, 2: "B", 3: None, 4: "C", 5: "A", 6: None}

def get_dia_hoy():
    return SEMANA.get(date.today().weekday())

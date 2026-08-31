from flask import Flask, render_template, request, redirect, jsonify, session
from datetime import date, datetime
from zoneinfo import ZoneInfo
from google import genai
import os
import json

app = Flask(__name__)
app.secret_key = "mauris-barber-shop-secret"

cites = []

CONTRASENYA_BARBER = "barber123"

ZONA_HORARIA = ZoneInfo("Europe/Madrid")

SERVEIS = {
    "Tall de cabell": 15,
    "Barba": 10,
    "Tall + barba": 20,
    "Tall + neteja facial": 25
}

HORES = [
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
    "16:00",
    "16:30",
    "17:00",
    "17:30",
    "18:00",
    "18:30"
]


def ara_madrid():
    return datetime.now(ZONA_HORARIA)


def minuts_hora(hora):
    hores, minuts = hora.split(":")
    return int(hores) * 60 + int(minuts)


def hora_disponible(dia, hora):
    ara = ara_madrid()
    avui = ara.date()

    try:
        dia_seleccionat = date.fromisoformat(dia)
    except ValueError:
        return False

    if dia_seleccionat < avui:
        return False

    if dia_seleccionat == avui:
        hora_possible = datetime.strptime(hora, "%H:%M").time()

        if hora_possible <= ara.time():
            return False

    for cita in cites:
        if cita["dia"] == dia and cita["hora"] == hora:
            return False

    return True


def obtenir_hores_disponibles(dia):
    disponibles = []

    for hora in HORES:
        if hora_disponible(dia, hora):
            disponibles.append(hora)

    return disponibles


def obtenir_hores_properes(dia, hora_demanada):
    disponibles = obtenir_hores_disponibles(dia)

    hora_base = minuts_hora(hora_demanada)

    disponibles.sort(
        key=lambda h: abs(minuts_hora(h) - hora_base)
    )

    return disponibles[:3]


def netejar_json_ia(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


@app.route("/")
def home():
    return render_template("index.html", serveis=SERVEIS)


@app.route("/login/client")
def login_client():
    session["rol"] = "client"
    return redirect("/reserva")


@app.route("/login/barber", methods=["GET", "POST"])
def login_barber():
    error = None

    if request.method == "POST":
        contrasenya = request.form.get("contrasenya")

        if contrasenya == CONTRASENYA_BARBER:
            session["rol"] = "barber"
            return redirect("/panelbarber")

        error = "Contrasenya incorrecta"

    return render_template("loginbarber.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/reserva")
def reserva():
    if session.get("rol") != "client":
        return redirect("/")

    return render_template(
        "reserva.html",
        serveis=SERVEIS,
        hores=HORES
    )


@app.route("/api/cites")
def api_cites():
    resultat = []

    for cita in cites:
        resultat.append({
            "title": "Ocupat",
            "start": cita["dia"] + "T" + cita["hora"]
        })

    return jsonify(resultat)


@app.route("/api/hores/<dia>")
def api_hores(dia):
    try:
        dia_seleccionat = date.fromisoformat(dia)
    except ValueError:
        return jsonify([])

    ara = ara_madrid()
    avui = ara.date()

    if dia_seleccionat < avui:
        return jsonify([])

    resultat = []

    for hora in HORES:
        passada = False
        ocupada = False

        if dia_seleccionat == avui:
            hora_cita = datetime.strptime(hora, "%H:%M").time()

            if hora_cita <= ara.time():
                passada = True

        for cita in cites:
            if cita["dia"] == dia and cita["hora"] == hora:
                ocupada = True
                break

        resultat.append({
            "hora": hora,
            "ocupada": ocupada,
            "passada": passada
        })

    return jsonify(resultat)


@app.route("/api/ia", methods=["POST"])
def api_ia():
    data = request.get_json() or {}

    peticio = data.get("peticio", "").strip()

    if not peticio:
        return jsonify({
            "ok": False,
            "missatge": "Escriu què necessites."
        })

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("ERROR GEMINI: no existeix GEMINI_API_KEY")

        return jsonify({
            "ok": False,
            "missatge": "La IA no està configurada correctament."
        })

    ara = ara_madrid()

    prompt = f"""
Ets l'assistent de reserves de Mauri's Barber Shop.

Has d'interpretar la petició d'un client i retornar NOMÉS un objecte JSON vàlid.

Avui és {ara.date().isoformat()}.
L'hora actual és {ara.strftime("%H:%M")} a Espanya.

Els serveis disponibles són exactament:
- Tall de cabell
- Barba
- Tall + barba
- Tall + neteja facial

Les hores disponibles de la barberia són:
{", ".join(HORES)}

Has d'entendre expressions en català com:
- avui
- demà
- demà passat
- dilluns
- dimarts
- dimecres
- dijous
- divendres
- dissabte
- diumenge
- al matí
- a la tarda
- cap a les 17
- a les 18
- el més aviat possible

Petició del client:
"{peticio}"

Retorna NOMÉS JSON amb aquest format:

{{
    "servei": "Tall de cabell, Barba, Tall + barba, Tall + neteja facial o null",
    "dia": "YYYY-MM-DD",
    "hora_preferida": "HH:MM o null",
    "franja": "mati, tarda o indiferent"
}}
"""

    try:
        client = genai.Client(api_key=api_key)

        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        print("RESPOSTA GEMINI COMPLETA:", resposta)

        if not resposta.text:
            raise Exception("Gemini no ha retornat text")

        print("TEXT GEMINI:", resposta.text)

        text_json = netejar_json_ia(resposta.text)

        print("JSON NETEJAT:", text_json)

        interpretacio = json.loads(text_json)

        print("JSON INTERPRETAT:", interpretacio)

    except Exception as error:
        print("ERROR GEMINI:", repr(error))

        return jsonify({
            "ok": False,
            "missatge": "No he pogut interpretar la petició. Prova d'escriure-la d'una altra manera."
        })

    servei = interpretacio.get("servei")
    dia = interpretacio.get("dia")
    hora_preferida = interpretacio.get("hora_preferida")
    franja = interpretacio.get("franja", "indiferent")

    if servei not in SERVEIS:
        servei = None

    try:
        dia_seleccionat = date.fromisoformat(dia)

    except (ValueError, TypeError):
        return jsonify({
            "ok": False,
            "missatge": "No he pogut identificar correctament el dia."
        })

    if dia_seleccionat < ara.date():
        return jsonify({
            "ok": False,
            "missatge": "La data interpretada ja ha passat."
        })

    disponibles = obtenir_hores_disponibles(dia)

    if franja == "mati":
        hores_franja = [
            h for h in disponibles
            if minuts_hora(h) < 14 * 60
        ]

        if hores_franja:
            disponibles = hores_franja

    elif franja == "tarda":
        hores_franja = [
            h for h in disponibles
            if minuts_hora(h) >= 14 * 60
        ]

        if hores_franja:
            disponibles = hores_franja

    if not disponibles:
        return jsonify({
            "ok": False,
            "missatge": "No queden hores disponibles per al dia que has demanat."
        })

    if hora_preferida:
        try:
            hora_base = minuts_hora(hora_preferida)

            disponibles.sort(
                key=lambda h: abs(
                    minuts_hora(h) - hora_base
                )
            )

        except Exception as error:
            print("ERROR ORDENANT HORES:", repr(error))

    recomanada = disponibles[0]
    alternatives = disponibles[1:3]

    return jsonify({
        "ok": True,
        "servei": servei,
        "dia": dia,
        "hora": recomanada,
        "alternatives": alternatives,
        "missatge": "He trobat una cita que encaixa amb la teva petició."
    })


@app.route("/api/reservar", methods=["POST"])
def api_reservar():
    data = request.get_json() or {}

    nom = data.get("nom", "").strip()
    servei = data.get("servei", "").strip()
    dia = data.get("dia", "").strip()
    hora = data.get("hora", "").strip()

    if not nom or not servei or not dia or not hora:
        return jsonify({
            "ok": False,
            "missatge": "Falten dades per completar la reserva."
        })

    try:
        dia_seleccionat = date.fromisoformat(dia)

    except ValueError:
        return jsonify({
            "ok": False,
            "missatge": "La data seleccionada no és correcta."
        })

    ara = ara_madrid()
    avui = ara.date()

    if dia_seleccionat < avui:
        return jsonify({
            "ok": False,
            "missatge": "No pots reservar una cita en un dia que ja ha passat."
        })

    if servei not in SERVEIS:
        return jsonify({
            "ok": False,
            "missatge": "El servei seleccionat no és correcte."
        })

    if hora not in HORES:
        return jsonify({
            "ok": False,
            "missatge": "L'hora seleccionada no és correcta."
        })

    if dia_seleccionat == avui:
        hora_cita = datetime.strptime(hora, "%H:%M").time()

        if hora_cita <= ara.time():
            return jsonify({
                "ok": False,
                "missatge": "Aquesta hora ja ha passat. Tria una hora posterior."
            })

    for cita in cites:
        if cita["dia"] == dia and cita["hora"] == hora:

            suggeriments = obtenir_hores_properes(
                dia,
                hora
            )

            return jsonify({
                "ok": False,
                "missatge": "Aquesta hora ja està ocupada.",
                "suggeriments": suggeriments
            })

    cites.append({
        "nom": nom,
        "servei": servei,
        "preu": SERVEIS[servei],
        "dia": dia,
        "hora": hora
    })

    return jsonify({
        "ok": True,
        "missatge": "Reserva creada correctament."
    })


@app.route("/panelbarber")
def panelbarber():
    if session.get("rol") != "barber":
        return redirect("/login/barber")

    ara = ara_madrid()
    avui = ara.date()

    cites_avui = []
    cites_futures = []
    cites_passades = []

    for index, cita in enumerate(cites):
        cita_panel = cita.copy()
        cita_panel["index"] = index

        dia_cita = date.fromisoformat(cita["dia"])

        hora_cita = datetime.strptime(
            cita["hora"],
            "%H:%M"
        ).time()

        if dia_cita < avui:
            cites_passades.append(cita_panel)

        elif dia_cita > avui:
            cites_futures.append(cita_panel)

        else:
            if hora_cita < ara.time():
                cites_passades.append(cita_panel)
            else:
                cites_avui.append(cita_panel)

    cites_avui.sort(
        key=lambda cita: cita["hora"]
    )

    cites_futures.sort(
        key=lambda cita: (
            cita["dia"],
            cita["hora"]
        )
    )

    cites_passades.sort(
        key=lambda cita: (
            cita["dia"],
            cita["hora"]
        ),
        reverse=True
    )

    return render_template(
        "panelbarber.html",
        cites_avui=cites_avui,
        cites_futures=cites_futures,
        cites_passades=cites_passades
    )


@app.route("/eliminar/<int:index>", methods=["POST"])
def eliminar_reserva(index):
    if session.get("rol") != "barber":
        return redirect("/login/barber")

    if 0 <= index < len(cites):
        cites.pop(index)

    return redirect("/panelbarber")


if __name__ == "__main__":
    app.run(debug=True)

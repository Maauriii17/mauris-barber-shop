from flask import Flask, render_template, request, redirect, jsonify, session

app = Flask(__name__)
app.secret_key = "mauris-barber-shop-secret"

cites = []

CONTRASENYA_BARBER = "barber123"

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

    ocupades = []

    for cita in cites:
        if cita["dia"] == dia:
            ocupades.append(cita["hora"])

    resultat = []

    for hora in HORES:
        resultat.append({
            "hora": hora,
            "ocupada": hora in ocupades
        })

    return jsonify(resultat)


@app.route("/api/reservar", methods=["POST"])
def api_reservar():

    data = request.get_json()

    nom = data.get("nom", "").strip()
    servei = data.get("servei", "").strip()
    dia = data.get("dia", "").strip()
    hora = data.get("hora", "").strip()

    if not nom or not servei or not dia or not hora:
        return jsonify({
            "ok": False,
            "missatge": "Falten dades per completar la reserva."
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

    for cita in cites:

        if cita["dia"] == dia and cita["hora"] == hora:

            lliures = []

            for h in HORES:

                ocupada = False

                for altra_cita in cites:
                    if altra_cita["dia"] == dia and altra_cita["hora"] == h:
                        ocupada = True
                        break

                if not ocupada:
                    lliures.append(h)

            return jsonify({
                "ok": False,
                "missatge": "Aquesta hora ja està ocupada.",
                "suggeriments": lliures[:3]
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

    cites_ordenades = sorted(
        cites,
        key=lambda cita: (cita["dia"], cita["hora"])
    )

    return render_template(
        "panelbarber.html",
        cites=cites_ordenades
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

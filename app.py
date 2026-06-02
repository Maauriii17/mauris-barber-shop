# app.py COMPLET

from flask import Flask, render_template, request, redirect, jsonify, session

app = Flask(__name__)
app.secret_key = "tdr123"

cites = []

# HOME
@app.route("/")
def home():
    return render_template("index.html")


# LOGIN
@app.route("/login/<rol>")
def login(rol):

    session["rol"] = rol

    # CLIENT → calendari
    if rol == "client":
        return redirect("/reserva")

    # BARBER → panel reserves
    if rol == "barber":
        return redirect("/panelbarber")

    return redirect("/")


# RESERVA
@app.route("/reserva")
def reserva():

    # si barber intenta entrar
    if session.get("rol") == "barber":
        return redirect("/panelbarber")

    return render_template("reserva.html")


# API CITES
@app.route("/api/cites")
def api_cites():
    return jsonify(cites)


# CREAR RESERVA
@app.route("/api/reservar", methods=["POST"])
def api_reservar():

    data = request.json

    # mirar si ocupada
    for c in cites:

        if c["start"] == data["start"]:

            hores = ["10:00", "11:00", "12:00", "17:00", "18:00"]

            ocupades = []

            for cita in cites:

                if data["start"][:10] == cita["start"][:10]:
                    ocupades.append(cita["start"][11:16])

            lliures = [h for h in hores if h not in ocupades]

            return jsonify({
                "ok": False,
                "suggestions": lliures
            })

    cites.append(data)

    return jsonify({"ok": True})


# PANEL BARBER
@app.route("/panelbarber")
def panel():

    # protecció barber
    if session.get("rol") != "barber":
        return "Accés denegat"

    return render_template(
        "panelbarber.html",
        cites=cites
    )


if __name__ == "__main__":
    app.run(debug=True)
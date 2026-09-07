"""Servidor Flask para Unity (patrón hw01 TC2008B).

python3 server.py            -> http://localhost:6769

POST /init   {"n_recipientes":3,"n_casillas":5,"voters_target":450,"seed":null}  -> estado inicial
GET  /step?n=1               -> avanza n beats, regresa estado
GET  /state                  -> estado actual sin avanzar
GET  /results                -> resultados finales + contadores
"""
from flask import Flask, jsonify, request

from model import CasillaModel

app = Flask(__name__)
model = CasillaModel()


@app.post("/init")
def init():
    global model
    p = request.get_json(silent=True) or {}
    model = CasillaModel(
        n_recipientes=int(p.get("n_recipientes", 3)),
        n_casillas=int(p.get("n_casillas", 5)),
        voters_target=int(p.get("voters_target", 450)),
        seed=p.get("seed"),
    )
    return jsonify(model.estado())


@app.get("/step")
def step():
    n = int(request.args.get("n", 1))
    for _ in range(n):
        if not model.running:
            break
        model.step()
    return jsonify(model.estado())


@app.get("/state")
def state():
    return jsonify(model.estado())


@app.get("/results")
def results():
    return jsonify(model.resultados())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6769, debug=False)

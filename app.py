import os
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from scrapers import buscar_en_tiendas
from bancos import BANCOS
from calculadora import valor_presente_cuotas, generar_veredicto

app = Flask(__name__)
CORS(app)

_cache = {}
INFLACION_MENSUAL_DEFAULT = 0.07


@app.route("/bancos", methods=["GET"])
def get_bancos():
    return jsonify(BANCOS)


@app.route("/buscar", methods=["POST"])
def buscar():
    data = request.json
    query = data.get("query", "").strip()
    banco_id = data.get("banco_id", "galicia")
    n_cuotas = int(data.get("cuotas", 6))
    inflacion = float(data.get("inflacion_mensual", INFLACION_MENSUAL_DEFAULT))

    if not query:
        return jsonify({"error": "Falta el producto"}), 400

    cache_key = f"{query.lower()}_{banco_id}_{n_cuotas}"
    if cache_key in _cache:
        return jsonify(_cache[cache_key])

    resultados_tiendas = asyncio.run(buscar_en_tiendas(query))

    if not resultados_tiendas:
        return jsonify({"error": "No encontré el producto en las tiendas"}), 404

    banco = BANCOS.get(banco_id, BANCOS["galicia"])
    plan = next((p for p in banco["planes"] if p["cuotas"] == n_cuotas), banco["planes"][0])
    tasa_banco = plan["tasa_mensual"]

    analisis = []
    for tienda in resultados_tiendas:
        if not tienda.get("precio_contado"):
            continue

        precio_contado = tienda["precio_contado"]
        precio_cuotas = tienda.get("precio_cuotas") or precio_contado

        resultado_vp = valor_presente_cuotas(precio_cuotas, n_cuotas, tasa_banco, inflacion)
        veredicto = generar_veredicto(precio_contado, resultado_vp)

        analisis.append({
            "tienda": tienda["tienda"],
            "nombre": tienda["nombre"],
            "precio_contado": precio_contado,
            "banco": banco["nombre"],
            "cuotas": n_cuotas,
            "tasa_banco_pct": round(tasa_banco * 100, 2),
            "cuota_mensual": resultado_vp["cuota_real"],
            "total_a_pagar": resultado_vp["total_a_pagar"],
            "vp_cuotas": resultado_vp["vp"],
            "recargo_pct": resultado_vp["recargo_pct"],
            "inflacion_acum_pct": resultado_vp["inflacion_acum_pct"],
            "veredicto": veredicto,
            "url": tienda.get("url"),
        })

    analisis.sort(key=lambda x: x["precio_contado"])

    respuesta = {
        "query": query,
        "resultados": analisis,
        "mejor_precio": analisis[0] if analisis else None
    }

    _cache[cache_key] = respuesta
    return jsonify(respuesta)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def valor_presente_cuotas(precio_total, n_cuotas, tasa_mensual, inflacion_mensual):
    if tasa_mensual > 0:
        cuota_real = precio_total * (tasa_mensual * (1 + tasa_mensual) ** n_cuotas) / \
                     ((1 + tasa_mensual) ** n_cuotas - 1)
    else:
        cuota_real = precio_total / n_cuotas

    vp = sum(cuota_real / ((1 + inflacion_mensual) ** t) for t in range(1, n_cuotas + 1))

    total_a_pagar = cuota_real * n_cuotas
    recargo_pct = ((total_a_pagar - precio_total) / precio_total) * 100
    inflacion_acum = ((1 + inflacion_mensual) ** n_cuotas - 1) * 100

    return {
        "vp": round(vp, 2),
        "cuota_real": round(cuota_real, 2),
        "total_a_pagar": round(total_a_pagar, 2),
        "recargo_pct": round(recargo_pct, 2),
        "inflacion_acum_pct": round(inflacion_acum, 2),
    }


def generar_veredicto(precio_contado, resultado_vp):
    vp = resultado_vp["vp"]
    diferencia = precio_contado - vp
    recargo = resultado_vp["recargo_pct"]
    inflacion_acum = resultado_vp["inflacion_acum_pct"]

    if vp < precio_contado:
        return {
            "decision": "cuotas",
            "titulo": "Conviene en cuotas",
            "detalle": f"En pesos de hoy las cuotas valen ${round(vp):,}. "
                       f"Ahorrás ${round(diferencia):,} respecto a pagar todo ahora.",
            "ahorro": round(diferencia, 2),
            "color": "green"
        }
    elif recargo <= inflacion_acum * 0.85:
        return {
            "decision": "cuotas",
            "titulo": "Cuotas razonables",
            "detalle": f"Recargo {recargo:.1f}% vs inflación ~{inflacion_acum:.0f}% del período. "
                       f"Las cuotas te convienen igual.",
            "ahorro": round(abs(diferencia), 2),
            "color": "green"
        }
    else:
        return {
            "decision": "contado",
            "titulo": "Conviene pagar contado",
            "detalle": f"El recargo {recargo:.1f}% supera la inflación esperada ({inflacion_acum:.0f}%). "
                       f"Pagá ahora y ahorrás ${round(abs(diferencia)):,}.",
            "ahorro": round(abs(diferencia), 2),
            "color": "red"
        }

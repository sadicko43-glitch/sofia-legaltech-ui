import re

def clasificar_tema(mensaje: str) -> str:
    mensaje = mensaje.lower().strip()

    # 1) Si el usuario responde solo con "<n> año(s)", es parte del flujo de vacaciones
    if re.fullmatch(r"\d+\s*(años|año)", mensaje):
        return "vacaciones"

    # 2) Saludos puros
    if mensaje in ["hola", "buenas", "hey", "buenos días", "buen dia"]:
        return "saludo"

    # 3) Pregunta genérica de días en el año
    if "días tiene el año" in mensaje or "dias tiene el año" in mensaje:
        return "general"

    # 4) Artículo de la LFT
    if re.search(r"art[ií]culo\s+\d+", mensaje):
        return "articulo"

    # 5) Pregunta explícita de vacaciones
    if "vacaciones" in mensaje and ("cuántos" in mensaje or "cuantos" in mensaje):
        return "vacaciones"

    # 6) Cálculo de finiquito (mencionan “finiquito” o meses)
    if "finiquito" in mensaje or re.search(r"\d+\s*mes", mensaje):
        return "finiquito"

    # 7) Renuncia
    if any(w in mensaje for w in ["renuncio", "renuncia", "quiero renunciar", "cómo renuncio"]):
        return "renuncia"

    # 8) Salario mínimo o salario en general
    if "salario mínimo" in mensaje or "salario minimo" in mensaje or "salario " in mensaje:
        return "salario"

    # 9) Autoría / Quién te creó
    if any(p in mensaje for p in [
        "quién te creó", "quien te creo", "quien te hizo",
        "quien te diseñó", "quien te programó", "quien es tu autor",
        "quien es tu creador", "desarrollado por", "diseñado por"
    ]):
        return "autor"

    # 10) Si no coincide nada, devolvemos None para fallback al modelo
    return None
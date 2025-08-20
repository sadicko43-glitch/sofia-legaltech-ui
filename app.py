# app.py
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/")
async def redirect_to_gradio():
    return RedirectResponse(url="/gradio")

import os
import re
import asyncio
import logging

from fastapi import Request, HTTPException
from fastapi.staticfiles import StaticFiles  # 👈 para servir archivos estáticos
from pydantic import BaseModel
from typing import List, Dict
from dotenv import load_dotenv

import gradio as gr
from gradio.themes import Base
from groq import Groq

from segmentador_lft import cargar_articulos_lft

# — Configuración de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# — Carga de entorno y datos
try:
    load_dotenv()
    ARTICULOS_LFT = cargar_articulos_lft()
except Exception as e:
    ARTICULOS_LFT = {}
    logger.error(f"Error al cargar artículos LFT: {e}")

REFORMAS_EXTENDIDAS = {
    "laboral": [
        "Outsourcing (2021): reforma que regula estrictamente la subcontratación laboral.",
        "Justicia laboral (2022): eliminación de Juntas, creación de Tribunales y Centros de Conciliación.",
        "Capacitismo (2022): prohibición de discriminación por discapacidad en empleo.",
        "Ley Silla (2024): obligación de proporcionar sillas o descansos a trabajadores de pie.",
        "Infonavit (2025): aportaciones obligatorias incluso en incapacidad (art. 29).",
        "Iniciativas LFT (2025): reformas a artículos 759 y 899-G para armonizar con Poder Judicial."
    ],
    "civil": [
        "Matrimonio igualitario (Jalisco y Veracruz, 2022).",
        "CNPCyF (2023–2025): código nacional para procedimientos civiles y familiares.",
        "Alimentos recíprocos (2025): obligación mutua entre padres e hijos mayores de 60.",
        "Digitalización notarial (2021): firma electrónica en testamentos y contratos.",
        "Ley de Amparo (2025): lenguaje incluyente, uso de UMA, limitación de efectos generales.",
        "Prohibición de matrimonio forzado en niñas indígenas (2024)."
    ],
    "salario_minimo": {
        "enero_2025": {
            "resto_pais": "$278.80 diarios / $8,364 mensuales",
            "zona_frontera": "$419.88 diarios / $12,596 mensuales",
            "exenciones": "Exento de ISR e IMSS; el empleador cubre IMSS",
            "ajuste_real": "Aumento neto ~7% ajustado por inflación (~4.75%)"
        }
    }
}

# 👈 Servir carpeta static
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []


def clasificar_tema(texto: str) -> str:
    msg = texto.lower().strip()
    logger.debug(f"Clasificando mensaje: {msg!r}")

    if re.fullmatch(r"^\s*\d+\s*años?\s*$", msg):
        return "vacaciones"
    if "liquidacion" in msg and "finiquito" in msg:
        return None
    if "vacaciones" in msg or "días de vacaciones" in msg or "dias de vacaciones" in msg:
        return "vacaciones"
    if any(w in msg for w in ["renuncio", "quiero renunciar", "cómo renuncio"]):
        return "renuncia"
    if "finiquito" in msg or re.search(r"\d+\s*mes", msg):
        return "finiquito"
    if "salario mínimo" in msg or "salario minimo" in msg or "salario " in msg:
        return "salario"
    if "cuántos días tiene el año" in msg or "cuantos dias tiene el año" in msg:
        return "general"
    if re.search(r"art[ií]culo\s+\d+", msg):
        return "articulo"
    if any(kw in msg for kw in [
        "quién te creó", "quien te creo", "quien te hizo",
        "quien te diseñó", "quien te programó", "quien es tu autor",
        "quien es tu creador", "desarrollado por", "diseñado por",
        "ingeniero y abogado", "origen", "origen del asistente"
    ]):
        return "autor"
    if msg in ["hola", "buenas", "buenos días", "buen dia", "hey"]:
        return "saludo"
    return None


def buscar_en_reformas(msg: str) -> str:
    m = msg.lower()
    if "salario mínimo" in m or "salario minimo" in m:
        d = REFORMAS_EXTENDIDAS["salario_minimo"]["enero_2025"]
        return (
            f"💵 Salario mínimo diario (enero 2025): {d['resto_pais']} (resto del país), "
            f"{d['zona_frontera']} (frontera norte). Exenciones: {d['exenciones']}. "
            f"Ajuste real: {d['ajuste_real']}."
        )
    claves = {
        "ley silla": REFORMAS_EXTENDIDAS["laboral"][3],
        "outsourcing": REFORMAS_EXTENDIDAS["laboral"][0],
        "justicia laboral": REFORMAS_EXTENDIDAS["laboral"][1],
        "infonavit": REFORMAS_EXTENDIDAS["laboral"][4]
    }
    for k, texto in claves.items():
        if k in m:
            return texto
    return ""


def respuesta_desactualizada(txt: str) -> bool:
    markers = [
        "no existe una ley llamada",
        "según datos de 2022",
        "actualmente el salario mínimo es de $140.70",
        "mi entrenamiento se basa en",
        "no tengo información actualizada"
    ]
    low = txt.lower()
    return any(marker in low for marker in markers)


async def llamar_modelo(client, msgs: List[Dict[str, str]]):
    return await asyncio.wait_for(
        asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",
            messages=msgs,
            temperature=0.2,
            max_tokens=1024
        ),
        timeout=10
    )


@app.post("/chat")
async def api_chat(request: Request, chat_req: ChatRequest):
    try:
        msg = chat_req.message.strip()
        tema = clasificar_tema(msg)
        logger.debug(f"Tema detectado: {tema!r}, mensaje: {msg!r}")

        if tema == "saludo":
            return {"reply": "¡Hola! ¿En qué aspecto del derecho laboral necesitas ayuda hoy?"}
        if tema == "general":
            return {"reply": "Un año común tiene 365 días. Si es bisiesto, 366."}
        if tema == "autor":
            return {
                "reply": (
                    "🎓 Soy SofIA, tu asistente legal desarrollado por el Ingeniero y Abogado "
                    "Zaihd Armando Gutiérrez Jiménez, basado en el modelo Llama 3.1 by Meta."
                )
            }
        if tema == "renuncia":
            return {
                "reply": (
                    "Para renunciar adecuadamente: entrega tu carta de renuncia por escrito, "
                    "guarda copia y notifica a Recursos Humanos. "
                    "No es obligatorio preaviso, pero se recomienda avisar con 30 días."
                )
            }
        if tema == "finiquito":
            m_low = msg.lower()
            match_m = re.search(r"(\d+)\s*mes", m_low)
            meses = int(match_m.group(1)) if match_m else None
            if meses is None:
                return {"reply": "⚠️ Indica cuántos meses llevas trabajando para calcular tu finiquito."}

            sal = re.search(r"([\d.,]+)\s*pesos\s+al\s+mes", m_low)
            if sal:
                mensual = float(sal.group(1).replace(",", ""))
                diario = mensual / 30.0
            else:
                raw = REFORMAS_EXTENDIDAS["salario_minimo"]["enero_2025"]["resto_pais"]
                diario = float(raw.replace("$", "").split()[0].replace(",", ""))

            días_aguinaldo = 15 * meses / 12
            monto_aguinalado = días_aguinaldo * diario
            días_vac = 6 * meses / 12
            monto_vac = días_vac * diario
            prima_vac = monto_vac * 0.25
            total = monto_aguinalado + monto_vac + prima_vac

            return {
                "reply": (
                    f"🧾 Finiquito tras {meses} meses con salario diario ${diario:.2f}:\n"
                    f"• Aguinaldo proporcional ({días_aguinaldo:.2f} días): ${monto_aguinalado:.2f}\n"
                    f"• Vacaciones proporcionales ({días_vac:.2f} días): ${monto_vac:.2f}\n"
                    f"• Prima vacacional: ${prima_vac:.2f}\n"
                    f"Total aproximado: ${total:.2f}"
                )
            }
        if tema == "salario":
            info = buscar_en_reformas(msg)
            return {"reply": info or "No encontré datos sobre salario mínimo."}
        if tema == "articulo":
            m1 = re.search(r"art[ií]culo\s+(\d+)", msg.lower())
            if m1:
                clave = f"Artículo {m1.group(1)}"
                cont = ARTICULOS_LFT.get(clave)
                if cont:
                    return {"reply": f"📘 {clave}:\n\n{cont}"}
                return {"reply": f"⚠️ No encontré el {clave} en la LFT vigente."}

        if tema == "vacaciones":
            m2 = re.search(r"^\s*(\d+)\s*años?\s*$", msg.lower())
            logger.debug(f"Regex vacaciones match: {m2!r}")
            if not m2:
                return {"reply": "⚠️ Por favor indica tus años de servicio, por ejemplo: '7 años'"}
            años = int(m2.group(1))

            if años == 1:
                días = 12
            elif años == 2:
                días = 14
            elif años == 3:
                días = 16
            elif años == 4:
                días = 18
            elif años == 5:
                días = 20
            elif 6 <= años <= 10:
                días = 22
            elif 11 <= años <= 15:
                días = 24
            elif 16 <= años <= 20:
                días = 26
            elif 21 <= años <= 25:
                días = 28
            elif 26 <= años <= 30:
                días = 30
            elif 31 <= años <= 35:
                días = 32
            else:
                días = 32

            return {
                "reply": (
                    f"📅 Según la reforma publicada en el DOF el 27-dic-2022 (Art.76 LFT), "
                    f"con {años} años de servicio tienes derecho a {días} días de vacaciones."
                )
            }

        # Contexto para Groq
        contexto = ""
        art_m = re.search(r"art[ií]culo\s+(\d+)", msg.lower())
        if art_m:
            contexto = ARTICULOS_LFT.get(f"Artículo {art_m.group(1)}", "")
        if not contexto:
            contexto = buscar_en_reformas(msg)
        if not contexto:
            contexto = ARTICULOS_LFT.get("Artículo 76", "")

        prompts = [{
            "role": "system",
            "content": (
                "Eres un asistente legal de la LFT. Usa SOLO este contexto:\n\n"
                f"{contexto}\n\nHabla claro, como a alguien con primaria."
            )
        }]
        for h in chat_req.history:
            prompts.append({"role": h["role"], "content": h["content"]})
        prompts.append({"role": "user", "content": msg})

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = await llamar_modelo(client, prompts)
        if not resp.choices:
            return {"reply": "⚠️ Sin respuesta del modelo. Intenta de nuevo."}
        salida = resp.choices[0].message.content.strip()
        if respuesta_desactualizada(salida):
            return {"reply": "⚠️ Respuesta no vigente. Consulta un artículo específico."}
        return {"reply": salida}

    except asyncio.TimeoutError:
        raise HTTPException(504, "⚠️ El modelo tardó demasiado.")
    except Exception as e:
        raise HTTPException(500, f"⚠️ Error interno: {e}")


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.get("/status")
async def root():
    return {"status": "API ok", "interface": "/gradio"}


# — Tema personalizado
custom_theme = Base(
    primary_hue="blue",
    secondary_hue="purple",
    text_size="md",
    radius_size="md",
)


def create_gradio_interface():
    with gr.Blocks(
        title="⚖️ SofIA LegalTech",
        theme=custom_theme,
        css="""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

:root {
    --primary-start: #1E3A8A;
    --primary-end:   #7C3AED;
    --accent:        #FFC107;
    --bg-page:       #000000;
    --card-bg:       #1F2937;
    --text-light:    #F5F3FF;
}

body {
    background-color: var(--bg-page) !important;
    font-family: 'Inter', sans-serif;
}

.gradio-container {
    max-width: 900px;
    margin: 20px auto;
    background: var(--card-bg) !important;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.24);
    overflow: hidden;
}

.gradio-container > div:nth-child(2) {
    display: flex !important;
    /* fila en lugar de columna */
    flex-direction: row !important;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--primary-start), var(--primary-end)) !important;
    padding: 24px;
    text-align: left !important;
    gap: 1rem !important;
}

/* ... el resto de tu CSS sigue igual ... */
"""
    ) as ui:

        # Header: logo y texto en la misma fila
        gr.HTML("""
        <div style="
            width:100%;
            margin-bottom:1rem;
            display:flex;
            align-items:center;
            justify-content:center;
            gap:1rem;
        ">
          <img src="/static/logo.png" alt="Logo SofIA"
               style="
                 width:140px;
                 height:140px;
                 object-fit:cover;
                 border-radius:50%;
                 box-shadow:0 4px 12px rgba(0,0,0,0.4);
               ">
          <div>
            <h2>⚖️ SofIA LegalTech</h2>
            <h4>Tu asistente legal laboral 100% gratuito</h4>
            <p><em>“Tu derecho no tiene precio”</em></p>
          </div>
        </div>
        """)

        # ... aquí continúa el resto de tu función sin cambios ...
        chatbot = gr.Chatbot(label="SofIA", type="messages", height=500)

        def greet():
            return [
                {"role": "assistant",
                 "content": (
                     "Hola, soy SofIA, tu asistente legal laboral 100% gratuito. "
                     "¿En qué puedo ayudarte hoy?"
                 )}
            ]
        ui.load(fn=greet, inputs=[], outputs=chatbot)

        with gr.Row():
            msg = gr.Textbox(placeholder="Escribe tu pregunta...", container=False)
            clear = gr.Button("Limpiar")

        def forward_to_api(user_msg, chat_hist):
            history_clean = [
                {"role": m["role"], "content": m["content"]}
                for m in chat_hist if isinstance(m, dict)
            ]
            history_clean.append({"role": "user", "content": user_msg})
            chat_req = ChatRequest(message=user_msg, history=history_clean)
            result = asyncio.run(api_chat(request=None, chat_req=chat_req))
            reply = result["reply"]
            history_clean.append({"role": "assistant", "content": reply})
            return history_clean, ""

        msg.submit(fn=forward_to_api, inputs=[msg, chatbot], outputs=[chatbot, msg])
        clear.click(fn=lambda: ([], ""), outputs=[chatbot, msg])

    return ui

# Montar Gradio dentro de FastAPI
gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(app, gradio_app, path="/gradio")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
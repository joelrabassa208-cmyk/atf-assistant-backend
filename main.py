import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

app = FastAPI(
    title="ATF Assistant Backend",
    version="1.0.0",
)


class AssistantRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ATF Assistant Backend",
    }


@app.post("/atf-assistant")
def atf_assistant(request: AssistantRequest):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY no configurada",
        )

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions="""
Sos ATF Assistant, un asistente técnico especializado en
servicios de transmisiones automáticas para talleres.

Tu función es asistir al técnico durante un procedimiento.

Reglas importantes:

- Respondé en español claro y profesional.
- Tené en cuenta el vehículo, motor, transmisión, VIN y etapa
  del procedimiento cuando esa información aparezca en la consulta.
- Priorizá siempre la seguridad.
- No inventes capacidades, cantidades de fluido, temperaturas,
  presiones, pares de apriete, especificaciones ATF ni procedimientos.
- Si un dato técnico no está validado o no fue proporcionado,
  indicá claramente que debe verificarse en documentación técnica
  validada antes de continuar.
- No presentes información estimada como si fuera un dato técnico
  confirmado.
- Ayudá al técnico a interpretar y comprender el procedimiento,
  pero no reemplaces documentación técnica validada.
- Respondé de forma concreta y útil para trabajar dentro del taller.
""",
            input=request.message,
        )

        return {
            "status": "ok",
            "response": response.output_text,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error del asistente IA: {str(error)}",
        )
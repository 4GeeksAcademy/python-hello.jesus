"""
Agente de Inventario — Suministros Carla
=========================================
Loop manual del agente (sin frameworks):
  Observar → Pensar → Actuar → Actualizar → Repetir
"""

import csv
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_BASE = "http://127.0.0.1:8000"
LOG_FILE = "conversation_log.csv"
LOG_FIELDS = ["actor", "message", "tool_call", "timestamp"]

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

SYSTEM_PROMPT = """Eres el Asistente Inteligente de Inventario para la empresa de suministros de cafetería de Carla.

### TUS HERRAMIENTAS:
NUNCA inventes cambios en el stock. Usa siempre una herramienta para leer o modificar datos.
1. `listar_productos` — Consulta todo el catálogo con cantidades y unidades.
2. `registrar_producto` — Añade un nuevo producto (nombre, cantidad, unidad, umbral_minimo).
3. `actualizar_stock` — Llama primero a listar_productos para obtener el product_id, luego usa este tool con el id y un delta (positivo = entrada, negativo = salida).
4. `obtener_alertas_stock` — Productos en o por debajo de su umbral mínimo.

### REGLAS:
- Si el usuario menciona un producto por nombre y necesitas su id, llama primero a listar_productos.
- Para múltiples acciones, ejecuta las herramientas una por una.
- Si falta información crítica (ej. unidad de medida), pregunta antes de actuar.
- Responde siempre en lenguaje natural fluido. Confirma las acciones con el stock resultante.
- Cuando pregunten por stock bajo o agotado, usa siempre obtener_alertas_stock."""

# ──────────────────────────────────────────────
# Definición de tools para el LLM
# ──────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "listar_productos",
            "description": "Consulta el catálogo completo: id, nombre, cantidad, unidad y umbral mínimo de cada producto.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_producto",
            "description": "Añade un nuevo producto al inventario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre del producto"},
                    "quantity": {"type": "number", "description": "Cantidad inicial en stock"},
                    "unit": {"type": "string", "description": "Unidad de medida (kg, litros, unidades, cajas…)"},
                    "min_threshold": {"type": "number", "description": "Stock mínimo para alerta. Por defecto: 10"},
                },
                "required": ["name", "quantity", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_stock",
            "description": (
                "Actualiza el stock de un producto existente usando su product_id. "
                "delta positivo = entrada (compra/entrega). delta negativo = salida (venta/merma). "
                "Si no conoces el product_id, llama primero a listar_productos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "ID único del producto (obtenido de listar_productos)"},
                    "delta": {"type": "number", "description": "Cantidad a sumar (positivo) o restar (negativo)"},
                },
                "required": ["product_id", "delta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_alertas_stock",
            "description": "Devuelve los productos con stock igual o inferior a su umbral mínimo configurado.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ──────────────────────────────────────────────
# Llamadas HTTP a la API (una por tool)
# ──────────────────────────────────────────────

def _call_api(method: str, path: str, **kwargs) -> dict:
    url = f"{API_BASE}{path}"
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "No se puede conectar con la API. ¿Está arrancada en el Terminal 1?"}
    except Exception as exc:
        return {"error": str(exc)}


def listar_productos() -> str:
    return json.dumps(_call_api("GET", "/inventory"), ensure_ascii=False)


def registrar_producto(name: str, quantity: float, unit: str, min_threshold: float = 10.0) -> str:
    payload = {"name": name, "quantity": quantity, "unit": unit, "min_threshold": min_threshold}
    return json.dumps(_call_api("POST", "/inventory", json=payload), ensure_ascii=False)


def actualizar_stock(product_id: str, delta: float) -> str:
    return json.dumps(
        _call_api("PATCH", f"/inventory/{product_id}", json={"delta": delta}),
        ensure_ascii=False,
    )


def obtener_alertas_stock() -> str:
    return json.dumps(_call_api("GET", "/inventory/alerts"), ensure_ascii=False)


TOOL_DISPATCH = {
    "listar_productos": lambda a: listar_productos(),
    "registrar_producto": lambda a: registrar_producto(**a),
    "actualizar_stock": lambda a: actualizar_stock(**a),
    "obtener_alertas_stock": lambda a: obtener_alertas_stock(),
}


# ──────────────────────────────────────────────
# Registro de conversación → conversation_log.csv
# ──────────────────────────────────────────────

def _log(actor: str, message: str, tool_call: str = "") -> None:
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "actor": actor,
                "message": message,
                "tool_call": tool_call,
                "timestamp": datetime.now().isoformat(),
            }
        )


# ──────────────────────────────────────────────
# Loop del agente: Observar → Pensar → Actuar → Actualizar → Repetir
# ──────────────────────────────────────────────

def run_agent(user_input: str, history: list[dict]) -> str:
    # OBSERVAR: añadir mensaje del usuario al historial
    history.append({"role": "user", "content": user_input})
    _log("user", user_input)

    while True:
        # PENSAR: el LLM decide si necesita una tool o puede responder
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=history,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=800,
        )

        msg = response.choices[0].message

        # Serializar el mensaje del asistente como dict para el historial
        msg_dict: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        history.append(msg_dict)

        # Sin tool calls → respuesta final
        if not msg.tool_calls:
            _log("assistant", msg.content or "")
            return msg.content or ""

        # ACTUAR: ejecutar cada tool solicitada
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            _log("assistant", f"Llamando a {fn_name}({fn_args})", tool_call=fn_name)

            if fn_name in TOOL_DISPATCH:
                result = TOOL_DISPATCH[fn_name](fn_args)
            else:
                result = json.dumps({"error": f"Herramienta '{fn_name}' no reconocida."})

            _log("tool", result, tool_call=fn_name)

            # ACTUALIZAR: inyectar resultado en el contexto antes de la siguiente iteración
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
        # REPETIR: el while vuelve a llamar al LLM con el contexto actualizado


# ──────────────────────────────────────────────
# Interfaz CLI
# ──────────────────────────────────────────────

def main() -> None:
    print("Asistente de Inventario listo. Escribe 'salir' para terminar.\n")
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("Carla: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAgente detenido.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("salir", "exit", "quit"):
            print("Hasta pronto.")
            break

        reply = run_agent(user_input, history)
        print(f"\nAsistente: {reply}\n")


if __name__ == "__main__":
    main()

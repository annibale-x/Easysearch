"""
title: Ghost Pipe POC - Survivor Edition
version: 0.1.7
author: Hannibal & AI
description: POC with guaranteed cleanup on STOP signal using try...finally pattern.
"""

import asyncio
import logging
import json
from typing import Optional, Any

# Open WebUI Imports
from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users

# --- CONFIGURAZIONE ---
DEBUG_MODE = True
TRIGGER_COMMAND = "!poc"

# --- LOGGING SETUP ---
logger = logging.getLogger("GhostPipePOC")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - 👻 %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

POC_PROMPT = """
Analyze the following text and provide a detaile text-only report.
Do not write preambles. Structure your response EXACTLY as follows:

## 🎯 Summary
[Write a 1-paragraph summary here]

## 📌 Main Topics
- [Topic 1]
- [Topic 2]

## 🚀 Key Takeaways
- [Takeaway 1]
- [Takeaway 2]

Text to analyze:
{TEXT}
"""


class Filter:
    def __init__(self):
        self.ghost_buffer = ""
        self.ghost_executed = False

    async def inlet(
        self,
        body: dict,
        __user__: dict = None,
        __event_emitter__: callable = None,
        __request__=None,
    ) -> dict:
        self.ghost_buffer = ""
        self.ghost_executed = False

        msg_list = body.get("messages", [])
        if not msg_list:
            return body

        # Estrazione trigger
        last_msg = msg_list[-1].get("content", "")
        txt = (
            "\n".join(
                [
                    str(p.get("text", ""))
                    for p in last_msg
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
            )
            if isinstance(last_msg, list)
            else str(last_msg)
        )
        txt = txt.strip()

        if txt.lower() != TRIGGER_COMMAND:
            return body

        logger.info(f"🚀 Ghost Pipe POC Attivato!")

        # Estrazione contesto (Ultimo messaggio assistente)
        target_text = ""
        for msg in reversed(msg_list[:-1]):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                target_text = content if isinstance(content, str) else str(content)
                break

        if not target_text:
            target_text = "Nessun testo dell'assistente trovato."

        shadow_body = {
            "model": body.get("model"),
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise analytical tool. Respond EXACTLY with the requested structure. NO PREAMBLES.",
                },
                {"role": "user", "content": POC_PROMPT.format(TEXT=target_text)},
            ],
            "stream": True,
            "temperature": 0.2,
        }

        user_obj = Users.get_user_by_id(__user__["id"]) if __user__ else None
        logger.info(f"Evocazione shadow request...")

        accumulated_text = ""

        try:
            response = await generate_chat_completion(
                __request__, shadow_body, user=user_obj
            )

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "👻 Ghost Pipe in esecuzione...",
                            "done": True,
                        },
                    }
                )

            iterator = (
                response.body_iterator
                if hasattr(response, "body_iterator")
                else response
            )

            # --- IL CUORE DEL SURVIVOR ---
            async for raw_chunk in iterator:
                chunk_str = (
                    raw_chunk.decode("utf-8")
                    if isinstance(raw_chunk, bytes)
                    else raw_chunk
                )
                chunk_text = ""

                for line in chunk_str.split("\n"):
                    line = line.strip()
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    try:
                        chunk_json = json.loads(line[6:])
                        if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                            chunk_text += (
                                chunk_json["choices"][0]
                                .get("delta", {})
                                .get("content", "")
                            )
                    except:
                        pass

                if not chunk_text:
                    continue
                accumulated_text += chunk_text

                if __event_emitter__:
                    # Se premi STOP, l'eccezione viene sollevata durante questo await
                    await __event_emitter__(
                        {"type": "message", "data": {"content": chunk_text}}
                    )
                    # await asyncio.sleep(0.005)

            logger.info("✅ Stream completato con successo.")

        except (asyncio.CancelledError, Exception) as e:
            # Se è una cancellazione (STOP), lo logghiamo qui
            if isinstance(e, asyncio.CancelledError):
                logger.warning("🛑 STOP RILEVATO: Task cancellato dall'utente.")
            else:
                logger.error(f"❌ Errore durante lo stream: {e}")
            # Rilanciamo l'eccezione per assicurarci che il task termini correttamente
            if isinstance(e, asyncio.CancelledError):
                raise

        finally:
            # --- CLEANUP GARANTITO ---
            # Anche se il task viene ucciso, Python esegue questo blocco.
            # Prepariamo il buffer per l'Outlet (e il DB).
            self.ghost_buffer = accumulated_text
            self.ghost_executed = True

            logger.info(
                f"💾 Cleanup: Salvati {len(self.ghost_buffer)} caratteri nel ghost_buffer."
            )

            if __event_emitter__:
                try:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Terminato (Sync)", "done": True},
                        }
                    )
                except:
                    pass

        return self._suppress_output(body)

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None
    ) -> dict:
        if self.ghost_executed and self.ghost_buffer:
            logger.info(
                f"Iniezione buffer nel DB via Outlet ({len(self.ghost_buffer)} chars)."
            )
            if "messages" in body and len(body["messages"]) > 0:
                body["messages"][-1]["content"] = self.ghost_buffer
            self.ghost_buffer = ""
            self.ghost_executed = False
        return body

    def _suppress_output(self, body: dict) -> dict:
        body["messages"][:-1] = [
            {
                "role": "user",
                "content": "Respond with exactly one single dot (.)",
            }
        ]
        body["temperature"] = 0.0
        body["num_predict"] = 1
        body["max_tokens"] = 1
        body["stream"] = False
        body["think"] = False
        body["seed"] = 42
        if "stop" in body:
            del body["stop"]
        return body

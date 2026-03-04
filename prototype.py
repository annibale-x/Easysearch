"""
title: Prototype
version: 0.0.1
author: Hannibal
https://github.com/annibale-x/open-webui-easybrief
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: WIP
"""

from pydantic import BaseModel
from typing import Optional


class Filter:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.sessions = {}

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        user_id = __user__.get("id", "default") if __user__ else "default"
        # Reset totale della sala operatoria
        self.sessions[user_id] = {"full_text": "", "is_inside": False, "buffer": ""}
        return body

    def stream(self, event: dict, __user__: Optional[dict] = None) -> dict:
        user_id = __user__.get("id", "default") if __user__ else "default"

        # Setup sessione di sicurezza
        if user_id not in self.sessions:
            self.sessions[user_id] = {"full_text": "", "is_inside": False, "buffer": ""}

        session = self.sessions[user_id]
        choices = event.get("choices", [])
        if not choices:
            return event

        content = choices[0].get("delta", {}).get("content", "")
        if not content:
            return event

        # 1. Aggiorniamo la "memoria globale" della risposta
        session["full_text"] += content

        # 2. Calcolo Matematico dello Stato
        # Quanti blocchi mermaid sono stati aperti?
        open_tags = session["full_text"].lower().count("```mermaid")
        # Quanti blocchi di codice (di qualsiasi tipo) ci sono in totale?
        all_tags = session["full_text"].count("```")
        # Le chiusure sono il totale meno le aperture
        close_tags = all_tags - open_tags

        # Se abbiamo più aperture che chiusure, stiamo attivamente scrivendo un diagramma
        currently_inside = open_tags > close_tags

        # --- GESTIONE DELLE TRANSIZIONI DI STATO ---

        # TRANSIZIONE A: Siamo appena ENTRATI in un blocco Mermaid
        if currently_inside and not session["is_inside"]:
            session["is_inside"] = True
            session["buffer"] = ""
            # INIEZIONE WATERMARK: Lo appiccichiamo all'ultimo pezzetto della parola "mermaid"
            event["choices"][0]["delta"]["content"] = (
                content + "\n%% 💉 SANITIZED BY MITM 💉 %%\n"
            )
            return event

        # TRANSIZIONE B: Siamo appena USCITI da un blocco Mermaid
        if not currently_inside and session["is_inside"]:
            session["is_inside"] = False

            # Qui applicheremo i metodi di sterilizzazione Python!
            # sanitized = _sterilize_graph(session["buffer"])
            sanitized = session["buffer"]  # Per ora pass-through

            # Rilasciamo il codice curato seguito dai backtick di chiusura (content)
            event["choices"][0]["delta"]["content"] = sanitized + content
            session["buffer"] = ""
            return event

        # STATO C: Siamo DENTRO il blocco (Buffering)
        if session["is_inside"]:
            session["buffer"] += content
            event["choices"][0]["delta"]["content"] = ""  # Nascondiamo i token alla UI
            return event

        # STATO D: Siamo FUORI dal blocco (Testo normale)
        return event

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        return body

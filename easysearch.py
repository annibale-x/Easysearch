"""
title: Easysearch - Web Search Assistant
version: 0.0.2
author: Hannibal
repo_url: https://github.com/annibale-x/EasySearch
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: Easy web search and summarize
"""

import json
import re
import time
import sys
import httpx  # type: ignore
from typing import Optional, Any, List, Dict, Tuple, Union
from pydantic import BaseModel, Field

# --- SURGICAL IMPORTS ---
from open_webui.main import app  # type: ignore
from open_webui.models.users import Users, UserModel  # type: ignore
from open_webui.utils.chat import generate_chat_completion  # type: ignore

# --- CONSTANTS ---
APP_ICON = "✨"
APP_NAME = "EasySearch"
OVERRIDE_WEB_SEARCH = None  # Set to True/False to override user setting
SUPPRESS_OUTPUT = False


HTTP_CLIENT = httpx.AsyncClient()


class ConfigService:
    """Service for handling configuration, valves, and internal state."""

    def __init__(self, ctx):
        """Initialize the ConfigService with context and default model state."""

        self.ctx = ctx
        self.valves, self.user_valves = ctx.valves, ctx.user_valves
        self.start_time = time.time()
        self.model = Store(
            {
                "trigger": ctx.valves.trigger_keyword,
                "debug": ctx.valves.debug or ctx.user_valves.debug,
                "user_query": "",
                "id": "",
                "executed": False,
                "web_search_original": False,
                "override_web_search": OVERRIDE_WEB_SEARCH,
                "suppress_output": SUPPRESS_OUTPUT,
            }
        )

    def _get_global_config(self, key: str, default: Any = None) -> Any:
        """Retrieve global configuration from the application state."""

        cfg = self.ctx.request.app.state.config
        val = default

        if hasattr(cfg, key):
            val = getattr(cfg, key)

        elif hasattr(cfg, "_state") and isinstance(cfg._state, dict):
            val = cfg._state.get(key, default)

        return val.value if hasattr(val, "value") else val


class Store(dict):
    """A dictionary subclass that allows attribute-style access."""

    def __getattr__(self, item):
        """Retrieve an item using attribute notation."""

        try:
            return self[item]

        except KeyError:
            return None

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class EmitterService:
    """Service for emitting events and status updates to the UI."""

    def __init__(self, event_emitter, ctx):
        """Initialize the EmitterService."""

        self.emitter, self.ctx = event_emitter, ctx

    async def emit_status(self, description: str, done: bool = False):
        """Emit a status update to the frontend."""

        if self.emitter:
            await self.emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    async def emit_citation(self, name: str, document: str, source: str):
        """Emit a citation to the frontend."""

        if self.emitter:
            await self.emitter(
                {
                    "type": "citation",
                    "data": {
                        "source": {"name": name},
                        "document": [document],
                        "metadata": [{"source": source}],
                    },
                }
            )


class DebugService:
    """Service for logging and dumping debug information."""

    def __init__(self, ctx):
        """Initialize the DebugService."""

        self.ctx = ctx

    def log(self, msg: str, is_error: bool = False):
        """Log a debug message to stderr."""

        is_debug = (
            self.ctx.ctx.model.debug if self.ctx.ctx else self.ctx.user_valves.debug
        )

        if is_debug or is_error:
            delta = time.time() - self.ctx.ctx.start_time if self.ctx.ctx else 0
            print(
                f"{'❌' if is_error else '⚡'} [{delta:+.2f}s] {APP_NAME} DEBUG: {msg}",
                file=sys.stderr,
                flush=True,
            )

    async def error(self, e: Any):
        """Log an error and emit an error message to the UI."""

        self.log(str(e), is_error=True)

        if self.ctx:
            self.ctx.output_content += f"\n\n❌ {APP_NAME} ERROR: {str(e)}\n"

            if self.ctx.ctx:
                self.ctx.ctx.model.executed = True

        if self.ctx.em.emitter:
            await self.ctx.em.emitter(
                {"type": "message", "data": {"content": f"\n\n❌ ERROR: {str(e)}"}}
            )

    def dump(self, data: Any = None, label: str = "DUMP"):
        """Dump a JSON representation of data to stderr for debugging."""

        is_debug = (
            self.ctx.ctx.model.debug if self.ctx.ctx else self.ctx.user_valves.debug
        )

        if not is_debug:
            return
        print(
            f"{'—'*60}\n📦 {APP_NAME} {label}:\n{json.dumps(data, indent=2, default=lambda o: str(o))}\n{'—'*60}",
            file=sys.stderr,
            flush=True,
        )

    def emit(self):
        """Generate a Markdown-formatted debug dump for the UI."""

        def _s(d):
            return {
                k: (
                    _s(v)
                    if isinstance(v, dict)
                    else (
                        f"{v[:4]}...{v[-4:]}"
                        if isinstance(v, str)
                        and ("key" in k.lower() or "auth" in k.lower())
                        else v
                    )
                )
                for k, v in d.items()
            }

        return (
            f"\n\n<details>\n"
            f"<summary>🔍 {APP_NAME} Debug</summary>\n\n"
            f"```json\n{json.dumps(_s(self.ctx.ctx.model), indent=2)}\n```\n\n"
            f"</details>"
        )


class NetworkService:
    """Service for handling HTTP requests."""

    def __init__(self, ctx):
        """Initialize the NetworkService."""

        self.ctx = ctx

    async def post(
        self, url: str, payload: dict, headers: dict = None, timeout: int = 120  # type: ignore
    ) -> httpx.Response:
        """Perform an asynchronous POST request."""

        if self.ctx.ctx.model.debug:
            self.ctx.debug.dump(payload, f"POST TO {url}")

        try:
            r = await HTTP_CLIENT.post(
                url, json=payload, headers=headers, timeout=timeout
            )
            r.raise_for_status()
            return r

        except Exception as e:

            if hasattr(e, "response") and e.response:  # type: ignore
                print(f"❌ HTTP ERROR BODY: {e.response.text}", file=sys.stderr)  # type: ignore
            await self.ctx.debug.error(f"POST {url} failed: {str(e)}")
            raise e

    async def get(
        self, url: str, params: dict = None, headers: dict = None  # type: ignore
    ) -> httpx.Response:
        """Perform an asynchronous GET request."""

        try:
            r = await HTTP_CLIENT.get(url, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            return r

        except Exception as e:
            await self.ctx.debug.error(f"GET failed: {str(e)}")
            raise e


class Filter:

    class Valves(BaseModel):
        debug: bool = Field(default=False)
        trigger_keyword: str = Field(
            default="??", description="Keyword to trigger the filter logic."
        )

    class UserValves(BaseModel):
        debug: bool = Field(default=False)

    def __init__(self):
        """Initialize the Filter with default valves and state."""

        self.valves, self.user_valves = self.Valves(), self.UserValves()
        self.request = self.debug = self.net = self.em = self.ctx = None
        self.output_content = ""

    async def inlet(
        self,
        body: dict,
        __user__: dict = None,  # type: ignore
        __event_emitter__: callable = None,  # type: ignore
        __request__=None,
    ) -> dict:
        """Process the incoming request and trigger filter logic if the keyword matches."""

        msg = body.get("messages", [])[-1].get("content", "")
        txt = (msg[0].get("text", "") if isinstance(msg, list) else str(msg)).strip()

        trigger = self.valves.trigger_keyword

        if not re.match(rf"^({re.escape(trigger)})(?:\s+|$)", txt, re.IGNORECASE):
            return body

        self.output_content = ""
        self.request = __request__
        uv_data = __user__.get("valves", {}) if __user__ else {}
        self.user_valves = (
            self.UserValves(**uv_data) if isinstance(uv_data, dict) else uv_data
        )

        self.ctx = ConfigService(self)
        self.debug, self.net, self.em = (
            DebugService(self),
            NetworkService(self),
            EmitterService(__event_emitter__, self),
        )

        # Web Search State Management
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )

        query = re.sub(rf"^{re.escape(trigger)}\s*", "", txt, flags=re.I).strip()
        self.ctx.model.user_query, self.ctx.model.id = query, body.get("model")

        try:
            await self.em.emit_status("Initializing...", False)

            # --- Logic Placeholders ---
            # Example: self.ctx.model.override_web_search = True

            # Apply Web Search Override if defined
            if self.ctx.model.override_web_search is not None:

                if "features" not in body:
                    body["features"] = {}

                body["features"]["web_search"] = self.ctx.model.override_web_search

            self.ctx.model.executed = True
            self.output_content += self.debug.emit()
            self.debug.log("--- INLET COMPLETE ---")
            await self.em.emit_status(f"{APP_NAME} Complete", True)

        except Exception as e:
            await self.debug.error(e)

        return self._suppress_output(body)

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None  # type: ignore
    ) -> dict:
        """Process the outgoing response and restore web search state."""

        if self.ctx and self.ctx.model.executed:
            # Restore Web Search original state

            if "features" in body:
                body["features"]["web_search"] = self.ctx.model.web_search_original

            # When suppress_output is True we want to exclusively manage output
            if self.ctx.model.suppress_output is True:
                if "messages" in body and len(body["messages"]) > 0:
                    body["messages"][-1]["content"] = self.output_content

            # When suppress_output is False we want to work on assistant message
            elif self.ctx.model.suppress_output is False:

                # ==> YOUR CODE HERE <==
                pass

            # Full pass-through mode
            else:
                pass

        self.debug.log("--- OUTLET COMPLETE ---")  # type: ignore
        return body

    def _suppress_output(self, body: dict) -> dict:
        """
        Wipes the history and suppresses output for synchronous commands.
        Skips suppression if web_search is enabled (after potential override).
        """

        ctx = self.ctx
        debug = self.debug

        if not ctx or not debug:
            return body

        if body.get("features", {}).get("web_search") is True:
            debug.log("Web search active: skipping suppression.")

            return body

        if ctx.model.suppress_output is True:
            debug.log("Suppressing output...")
            body["messages"][:] = [{"role": "user", "content": "."}]
            body["temperature"] = 0.0
            body["max_tokens"] = 1
            body["stream"] = False

            if "stop" in body:
                del body["stop"]

        return body

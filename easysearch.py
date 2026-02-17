"""
title: EasyBrief - Information & Search Assistant
version: 0.0.3
author: Hannibal
repo_url: https://github.com/annibale-x/EasySearch
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: Easy web search, analysis and visual restructuring
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
APP_NAME = "EasyBrief"
OVERRIDE_WEB_SEARCH = None  # Set to True/False to override user setting
SUPPRESS_OUTPUT = False

BRIEF_PROMPT = """
Analyze the provided information and reorganize it for immediate visual comprehension following these strict rules:

1. VISUAL FIRST (TABLES): Convert ANY list of items with multiple attributes into a Markdown TABLE. 
   - Examples: Lists of people (Name | Role/Discipline | Achievement), products (Model | Specs | Price), or events (Date | Event | Location).
   - If you see comparative data, technical specifications, or pros/cons, use a TABLE.

2. LOGIC & PROCESSES (DIAGRAMS): Represent workflows, timelines, cause-effect relationships, or hierarchies using MERMAID DIAGRAMS.
   - Use `graph TD` for hierarchies or flows.
   - Use `sequenceDiagram` for interactions.
   - Use `pie` for percentages or distributions.

3. TEXT MANAGEMENT (SAY NO TO BULLET WALLS): 
   - DO NOT use long bullet point lists (more than 5 items). If a list is long, it MUST be converted into a Table or a Diagram.
   - If a section is short and clear (max 2-3 lines), keep it as is.
   - Summarize verbose sections into a single paragraph of maximum 3 lines.

4. HIERARCHY & EMOJIS: Use clear headings (##, ###) and relevant emojis.
   - MANDATORY: Emojis must ALWAYS be placed BEFORE the heading or category text, never at the end.

5. SUMMARY & CLEANLINESS: 
   - Conclude with a "📌 Key Takeaways" box using a blockquote (>). 
   - MANDATORY: Do not add any introductory or concluding remarks, meta-talk, or explanations about the format. The output must end exactly at the Key Takeaways box.

GOAL: The user must understand the main concepts at a single glance. Minimize vertical scrolling by using horizontal structures like tables.
"""


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
                "brief_trigger": ctx.valves.brief_trigger_keyword,
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
            f"\n\n<details>\n\n"
            f"<summary>🔍 {APP_NAME} Debug</summary>\n\n"
            f"```json\n{json.dumps(_s(self.ctx.ctx.model), indent=2)}\n```\n\n"
            f"</details>"
        )


class Filter:

    class Valves(BaseModel):
        debug: bool = Field(default=False)
        trigger_keyword: str = Field(
            default="??", description="Trigger for Web Search + Analysis."
        )
        brief_trigger_keyword: str = Field(
            default="!!", description="Trigger for Text Analysis/Restructuring."
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
        """Process the incoming request and trigger filter logic based on keywords."""

        msg_list = body.get("messages", [])

        if not msg_list:
            return body

        last_msg = msg_list[-1].get("content", "")
        txt = (
            last_msg[0].get("text", "") if isinstance(last_msg, list) else str(last_msg)
        ).strip()

        trg_search = self.valves.trigger_keyword
        trg_brief = self.valves.brief_trigger_keyword

        # Regex to detect triggers and optional content
        m_search = re.match(
            rf"^({re.escape(trg_search)})(?:\s+|$)(.*)", txt, re.S | re.I
        )
        m_brief = re.match(rf"^({re.escape(trg_brief)})(?:\s+|$)(.*)", txt, re.S | re.I)

        if not m_search and not m_brief:
            return body

        self.output_content = ""
        self.request = __request__
        uv_data = __user__.get("valves", {}) if __user__ else {}
        self.user_valves = (
            self.UserValves(**uv_data) if isinstance(uv_data, dict) else uv_data
        )

        self.ctx = ConfigService(self)
        self.debug, self.em = (
            DebugService(self),
            EmitterService(__event_emitter__, self),
        )

        # Web Search State Management
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )

        mode_search = bool(m_search)
        content = (m_search.group(2) if mode_search else m_brief.group(2)).strip()

        # Handle Contextual/Empty Triggers
        if not content and len(msg_list) > 1:
            prev_content = msg_list[-2].get("content", "")
            content = (
                prev_content[0].get("text", "")
                if isinstance(prev_content, list)
                else str(prev_content)
            )
            self.debug.log(f"Empty trigger detected. Using context: {content[:50]}...")

        self.ctx.model.user_query, self.ctx.model.id = content, body.get("model")

        try:
            await self.em.emit_status("EasyBrief Analysis...", False)

            # Logic: Force Search if ??, Disable if !!
            if mode_search:
                self.ctx.model.override_web_search = True

            else:
                self.ctx.model.override_web_search = False

            # Inject the Briefing System Prompt
            instr = f"{BRIEF_PROMPT}\n\nINPUT TO PROCESS:\n{content}"
            body["messages"][-1]["content"] = instr

            # Apply Web Search Override
            if self.ctx.model.override_web_search is not None:

                if "features" not in body:
                    body["features"] = {}

                body["features"]["web_search"] = self.ctx.model.override_web_search

            self.ctx.model.executed = True
            self.debug.log(f"Execution Mode: {'Search' if mode_search else 'Brief'}")
            await self.em.emit_status(f"{APP_NAME} Working", False)

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
                    body["messages"][-1]["content"] = (
                        self.output_content + self.debug.emit()
                    )

            # When suppress_output is False we append debug info if needed
            elif self.ctx.model.suppress_output is False:

                if "messages" in body and len(body["messages"]) > 0:
                    body["messages"][-1]["content"] += self.debug.emit()

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

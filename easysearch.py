"""
title: EasyBrief - Information & Search Assistant
version: 0.0.7
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
Analyze the input and reorganize it into a SINGLE unified executive report using an ADAPTIVE VISUAL APPROACH. 
Break down the information into logical sections. For each section, provide a brief (max 2 lines) introductory context followed by the most suitable visual representation:

1. LANGUAGE & SEARCH PROTOCOL (STRICT):
   - DETECT the language of the 'INPUT TO PROCESS' below.
   - MANDATORY: You MUST perform the web search and write the entire response in that SAME language.

2. DATA, COMPARISONS, CHRONOLOGIES & PROJECTIONS (TABLES - BODY TEXT ONLY):
   - Use standard Markdown TABLES for all data lists, technical comparisons, chronologies, and financial projections.
   - MANDATORY: Write tables DIRECTLY in the message body. 
   - FORBIDDEN: NEVER use triple backticks (```) or single backticks (`) for tables.
   - FORBIDDEN: NEVER use the word "markdown" to label tables.
   - START the table immediately with the pipe character (|).
   - MANDATORY: Ensure there is exactly one empty line before and after every table.
   - FORBIDDEN: Do not use Mermaid for timelines, gantt charts, or numerical projections.

3. LOGIC, FLOWS & STRUCTURES (MERMAID DIAGRAMS):
   - MANDATORY: Use ONLY the ```mermaid code block for diagrams (you MUST include the word 'mermaid' after the first three backticks).
   - MANDATORY SYNTAX: Always wrap all text labels and node names in double quotes (e.g., A["Label (Text)"]).
   - PROCESSES: Use `graph TD` or `graph LR` for workflows.
   - INTERACTIONS: Use `sequenceDiagram` for communication between actors.
   - DISTRIBUTIONS: Use `pie` for market shares.
   - HIERARCHIES: Use `mindmap` or `graph TD` for breakdowns.
   - FORBIDDEN: Never use `timeline` or `gantt` keywords.

4. TEXT & CONTEXT MANAGEMENT:
   - BALANCED APPROACH: Every visual element MUST be preceded by a concise 1-2 line explanation or insight that summarizes the data shown.
   - NO BULLET WALLS: If a list has >5 items, it MUST be converted into a Table or Diagram.
   - SPACING: Insert a horizontal divider (---) between every main section to improve readability.
   - SUMMARY: Summarize verbose text aggressively, keeping any non-visual text block under 3 lines.

5. HIERARCHY & EMOJIS: 
   - Use clear headings (##, ###).
   - MANDATORY: Relevant emojis must ALWAYS be placed BEFORE the heading or category text.

6. SUMMARY & CLEANLINESS: 
   - Conclude with a "📌 Key Takeaways" box using a blockquote (>). 
   - MANDATORY: Do not add any introductory or concluding remarks, meta-talk, or explanations about the format. The output must end exactly at the Key Takeaways box.

CRITICAL RECAP: 
- Tables: NO backticks, NO code blocks.
- Mermaid: YES backticks, YES 'mermaid' label.
- Goal: Professional executive summary.
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

    def _parse_trigger(self, txt: str) -> Optional[dict]:
        """Validate input and parse trigger, language, and content."""

        s_trg = self.valves.trigger_keyword
        b_trg = self.valves.brief_trigger_keyword

        # Check which trigger starts the text
        active = (
            s_trg
            if txt.startswith(s_trg)
            else (b_trg if txt.startswith(b_trg) else None)
        )

        if not active:
            return None

        # Extract everything after the trigger
        remainder = txt[len(active) :]
        lang = None

        # Check for :lang syntax (e.g. :it)
        if remainder.startswith(":"):
            lang = remainder[1:3]
            remainder = remainder[3:]

        return {
            "is_search": active == s_trg,
            "lang": lang,
            "content": remainder.strip(),
        }

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

        # Phase 1: Parsing & Validation
        parsed = self._parse_trigger(txt)

        if not parsed:
            return body

        # Phase 2: Initialization
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

        # Phase 3: State Management
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )
        self.ctx.model.forced_language = parsed["lang"]
        content = parsed["content"]

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

            # Apply Web Search Override logic
            self.ctx.model.override_web_search = parsed["is_search"]

            # Build Language Instruction
            lang_instr = (
                f"MANDATORY: Respond in {parsed['lang'].upper()}."
                if parsed["lang"]
                else "DETECT and match the input language."
            )

            # Inject the Briefing System Prompt
            instr = f"{BRIEF_PROMPT}\n\n{lang_instr}\n\nINPUT TO PROCESS:\n{content}"
            body["messages"][-1]["content"] = instr

            if self.ctx.model.override_web_search is not None:

                if "features" not in body:
                    body["features"] = {}

                body["features"]["web_search"] = self.ctx.model.override_web_search

            self.ctx.model.executed = True
            self.debug.log(
                f"Execution Mode: {'Search' if parsed['is_search'] else 'Brief'} | Lang: {parsed['lang'] or 'Auto'}"
            )
            await self.em.emit_status(f"{APP_NAME} Working", False)

        except Exception as e:
            await self.debug.error(e)

        return self._suppress_output(body)

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None  # type: ignore
    ) -> dict:
        """Process the outgoing response and restore web search state."""

        if self.ctx and self.ctx.model.executed:

            if "messages" in body and len(body["messages"]) > 0:
                self.ctx.model.raw_assistant_response = body["messages"][-1].get(
                    "content", ""
                )

            if "features" in body:
                body["features"]["web_search"] = self.ctx.model.web_search_original

            if self.ctx.model.suppress_output is True:

                if "messages" in body and len(body["messages"]) > 0:
                    body["messages"][-1]["content"] = (
                        self.output_content + self.debug.emit()
                    )

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

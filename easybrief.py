"""
title: EasyBrief - Web Search & Executive Summaries
version: 0.1.7
author: Hannibal
https://github.com/annibale-x/open-webui-easybrief
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: Transform text and web search results into structured Executive Reports with tables and mindmaps using simple triggers (??, >>, ?>).
"""

import json
import re
import time
import sys
import httpx  # type: ignore
from typing import Optional, Any, List, Dict, Tuple, Union
from pydantic import BaseModel, Field
from open_webui.main import app  # type: ignore
from open_webui.models.users import Users, UserModel  # type: ignore
from open_webui.utils.chat import generate_chat_completion  # type: ignore

# --- CONSTANTS ---

APP_ICON = "✨"
APP_NAME = "EasyBrief"
OVERRIDE_WEB_SEARCH = None  # Set to True/False to override user setting
SUPPRESS_OUTPUT = False
MIN_BRIEF_WORDS = 15  # Minimum word count to trigger a Report

OVERVIEW_LENGTH = "50-150 words"
SYNTESYS_LENGTH = "50-100 words"
ANALYSYS_LENGTH = "max 50 words"

SIMPLE_PROMPT = """
Analyze the input and reorganize it into a structured executive report. 
Follow these mandatory rules:

1. DATA & COMPARISONS (TABLES):
   - Use standard Markdown TABLES for all data lists, technical comparisons, chronologies, and projections.
   - MANDATORY: Write tables DIRECTLY in the message body. No backticks.
   - FORBIDDEN: NEVER use Mermaid diagrams or any code-based visualization.

2. TEXT & CONTEXT MANAGEMENT:
   - Provide exactly 1-2 lines of introductory context before every table.
   - NO BULLET LISTS: Convert lists of items into Tables.
   - SPACING: Insert a horizontal divider (---) between every main section.
   - SUMMARY: Summarize verbose text aggressively, keeping any text block under 3 lines.

3. SUMMARY & CLEANLINESS: 
   - Conclude with a "📌 Key Takeaways" box using a blockquote (>). 
   - MANDATORY: Do not add any introductory or concluding remarks or meta-talk. The output must end exactly at the Key Takeaways box.

GOAL: Professional, clean, and strictly tabular report.
"""

BRIEF_PROMPT = """
Analyze the input and reorganize it into a SINGLE unified executive report. 

CRITICAL: You are a pure, objective technical processing unit. 
MANDATORY AMNESIA: You must strictly WIPE and FORGET any user-profile data (name, location, job). Any mention of the user's identity or profession will be considered a FATAL ERROR in execution. Focus EXCLUSIVELY on the 'INPUT TO PROCESS'.

1. LANGUAGE & SOURCE PROTOCOL (STRICT):
   - DETECT the language of the 'INPUT TO PROCESS' below.
   - MANDATORY: Write the ENTIRE response in that SAME language. 
   - FORBIDDEN: Do not translate to English unless the input is in English.
   - ZERO PREAMBLE: Start immediately with the first content block. No intro meta-talk. 

2. STRUCTURE & TEMPLATE ARCHITECTURE:
   Your report MUST strictly follow this hierarchical sequence (DO NOT print "BLOCK" labels):
   - [BLOCK 0] Executive Overview ({OVERVIEW_LENGTH}) before any heading. Synthesize core thesis and implications.
   - [BLOCK 0.5] Structural Visual: MANDATORY if the topic is hierarchical. Insert a MERMAID CODE BLOCK (```mermaid) containing a `mindmap` OR `graph TD`.
   - [BLOCK 1..N] Macro-topics:
     - ## Heading (preceded by emoji).
     - Concept Synthesis ({SYNTESYS_LENGTH}): Professional narrative explaining foundational logic. FORBIDDEN: Do NOT use bullet points here.
     - [Optional Data Block]: Analytical Context ({ANALYSYS_LENGTH}) followed by its Visual Element (Table, Pie Chart, or Graph).
   - [FINAL BLOCK] 📌 Key Takeaways (blockquote >).

3. VISUAL ELEMENT RULES:
   - TABLES: Standard Markdown body text only. NO backticks. Start immediately with the pipe (|). MANDATORY: Exactly one empty line before and after every table.
   - MERMAID GRAPH: MANDATORY: Wrap code in triple backticks (```mermaid). Use `graph TD` exclusively. Use ONLY square brackets `["Text"]` for nodes. ALWAYS wrap text in double quotes.
   - MERMAID PIE: MANDATORY for market shares or percentage distributions. Wrap labels in double quotes.
   - VISUAL ACCESSIBILITY: Ensure high contrast (dark text on light nodes, light text on dark nodes).
   - NARRATIVE PRIORITY: Every visual element MUST be preceded by its own Analytical Context block.
   - NO BULLET POINTS (STRICT): Bullet lists are FORBIDDEN. Convert simple lists into TABLES. For multi-level/nested lists, YOU MUST split them into specific Sub-headings (###) containing their own dedicated Tables.

4. MERMAID VALID SYNTAX

```mermaid
graph TD
    A["Main System"] --> B["Subsystem 1"]
    A --> C["Subsystem 2"]
    B --> D["Leaf Component"]
```

```mermaid
graph TD
    A["Human Nervous System"] 
        -->|CNS| B["Brain"]
        -->|CNS| E["Spinal Cord"]
        -->|PNS| F["Somatic Nervous System"]
        -->|PNS| G["Autonomic Nervous System"]
    B --> D["Sympathetic Nervous System"]
    B --> E["Parasympathetic Nervous System"]
```

```mermaid
mindmap
  root((Main Subject))
    Logical Branch
      Sub-detail
```

5. REFERENCE TEMPLATE:

## 🎯 Executive Overview

A dense {OVERVIEW_LENGTH} words summary.

```mermaid
graph TD
    A["Main Concept"] --> B["Component"]
```

---
## ⚙️ Foundational Logic

**Concept Synthesis**: 
{SYNTESYS_LENGTH} words block. Do NOT use bullet points here. Write a cohesive narrative.

**Analytical Insight**: 
{ANALYSYS_LENGTH} words block.

| Dimension | Impact |
|-----------|--------|
| Logic A   | High   |

---
📌 Key Takeaways
Concise summary points (bullet list).


CRITICAL RECAP: 
- Flow: Overview -> Visual -> Heading -> Synthesis (Must be {SYNTESYS_LENGTH}, NO BULLETS) -> Analysis -> Table/Graph.
- Respond ONLY in the input language (No English translation).
- Mermaid: Square nodes `["Text"]` only. Double quotes required.
- Mindmap: root((Text)) and 2-space indentation. No quotes.
- Tables: NO backticks. Pipe (|) start. One empty line before/after.
- The output must end exactly at the Key Takeaways box.
- No bullets: Convert lists of items into Tables.
- Use 🎯 as emoji in the overview.
- Use 📌 as emoji in the Key Takeaways.
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
                "search_trigger": ctx.valves.search_trigger,
                "brief_trigger": ctx.valves.brief_trigger,
                "search_and_brief_trigger": ctx.valves.search_and_brief_trigger,
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

        # UI Debug is strictly User-controlled to prevent visual pollution
        if not self.ctx.user_valves.debug:
            return ""

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
        search_trigger: str = Field(
            default="??",
            description="Trigger for Web Search only (exactly 2 chars, e.g. '?? query').",
            min_length=2,
            max_length=2,
        )
        brief_trigger: str = Field(
            default=">>",
            description="Trigger for Brief/Analysis only (exactly 2 chars, e.g. '>> text').",
            min_length=2,
            max_length=2,
        )
        search_and_brief_trigger: str = Field(
            default="?>",
            description="Trigger for Web Search + Brief Analysis (exactly 2 chars, e.g. '?> query').",
            min_length=2,
            max_length=2,
        )

    class UserValves(BaseModel):
        rich_output: bool = Field(
            default=True,
            description="Enable Mermaid diagrams and advanced visual layout.",
        )
        debug: bool = Field(default=False)

    def __init__(self):
        """Initialize the Filter with default valves and state."""

        self.valves, self.user_valves = self.Valves(), self.UserValves()
        self.request = self.debug = self.net = self.em = self.ctx = None
        self.output_content = ""

    def _parse_trigger(self, txt: str) -> Optional[dict]:
        """Validate input and parse trigger, language, and content."""

        # Normalize "Smart Punctuation" (iOS/macOS/Android) to ASCII triggers
        # We only replace the FIRST occurrence to avoid altering the message content
        smart_map = {"»": ">>", "«": "<<", "—": "--", "–": "--", "→": "->", "←": "<-"}

        for smart, ascii_val in smart_map.items():
            if txt.startswith(smart):
                txt = txt.replace(smart, ascii_val, 1)
                break

        # Define trigger mapping with priorities
        # Priority order matters if user customizes triggers to have prefix overlaps
        triggers = [
            (self.valves.search_and_brief_trigger, True, True),  # ?> (Search + Brief)
            (self.valves.brief_trigger, False, True),  # >> (Brief Only)
            (self.valves.search_trigger, True, False),  # ?? (Search Only)
        ]

        active_trigger = None
        is_search = False
        is_brief = False

        # Identify which trigger starts the text
        for trigger, search_flag, brief_flag in triggers:
            if txt.startswith(trigger):
                active_trigger = trigger
                is_search = search_flag
                is_brief = brief_flag
                break

        if not active_trigger:
            return None

        # Extract everything after the trigger
        remainder = txt[len(active_trigger) :]
        lang = None

        # Check for :lang syntax (e.g. :it)
        if remainder.startswith(":"):
            lang = remainder[1:3]
            remainder = remainder[3:]

        return {
            "is_search": is_search,
            "is_brief": is_brief,
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

        self.ctx = None

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
            await self.em.emit_status("EasyBrief Analysis..", False)

            # Apply Web Search Override logic
            self.ctx.model.override_web_search = parsed["is_search"]

            # Build Language Instruction
            lang_instr = (
                f"MANDATORY: Respond in {parsed['lang'].upper()}."
                if parsed["lang"]
                else "DETECT and match the input language."
            )

            # Decision Logic: Quick Search vs Briefing
            if parsed["is_brief"]:
                selected_prompt = (
                    BRIEF_PROMPT if self.user_valves.rich_output else SIMPLE_PROMPT
                )

                # Dynamic injection of length constraints
                if self.user_valves.rich_output:
                    selected_prompt = (
                        selected_prompt.replace("{OVERVIEW_LENGTH}", OVERVIEW_LENGTH)
                        .replace("{SYNTESYS_LENGTH}", SYNTESYS_LENGTH)
                        .replace("{ANALYSYS_LENGTH}", ANALYSYS_LENGTH)
                    )

                instr = (
                    f"{selected_prompt}\n\n{lang_instr}\n\nINPUT TO PROCESS:\n{content}"
                )

            else:
                # Trigger '?' (Quick Search) mode: skip mega-instructions
                instr = f"{lang_instr}\n\nINPUT TO PROCESS:\n{content}"

            body["messages"][-1]["content"] = instr

            # If briefing is active, we strip the history to prevent user-profile bias
            # and focus the model's attention solely on the current task.
            if parsed["is_brief"]:
                body["messages"] = [body["messages"][-1]]
                self.debug.log("History wiped: Isolation Mode active.")

            if self.ctx.model.override_web_search is not None:

                if "features" not in body:
                    body["features"] = {}

                body["features"]["web_search"] = self.ctx.model.override_web_search

            self.ctx.model.executed = True
            self.debug.log(
                f"Execution Mode: {'Search' if parsed['is_search'] else 'Brief'} | Briefing: {parsed['is_brief']} | Lang: {parsed['lang'] or 'Auto'}"
            )
            await self.em.emit_status(f"{APP_NAME} Working..", False)

        except Exception as e:
            await self.debug.error(e)

        return self._suppress_output(body)

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None  # type: ignore
    ) -> dict:
        """Process the outgoing response and restore web search state."""

        if self.ctx and self.ctx.model.executed:

            await self.em.emit_status(f"{APP_NAME} Done", True)

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
            await self.em.emit_status(f"{APP_NAME} Done", True)

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

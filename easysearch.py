"""
title: EasyBrief - Information & Search Assistant
version: 0.1.2
author: Hannibal
repo_url: https://github.com/annibale-x/EasyBrief
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



SIMPLE_PROMPT = """
Analyze the input and reorganize it into a structured executive report. 
Follow these mandatory rules:

1. DATA & COMPARISONS (TABLES):
   - Use standard Markdown TABLES for all data lists, technical comparisons, chronologies, and projections.
   - MANDATORY: Write tables DIRECTLY in the message body. No backticks.
   - FORBIDDEN: NEVER use Mermaid diagrams or any code-based visualization.

2. TEXT & CONTEXT MANAGEMENT:
   - Provide exactly 1-2 lines of introductory context before every table.
   - NO BULLETS: Convert lists of items into Tables.
   - SPACING: Insert a horizontal divider (---) between every main section.
   - SUMMARY: Summarize verbose text aggressively, keeping any text block under 3 lines.

3. SUMMARY & CLEANLINESS: 
   - Conclude with a "📌 Key Takeaways" box using a blockquote (>). 
   - MANDATORY: Do not add any introductory or concluding remarks or meta-talk. The output must end exactly at the Key Takeaways box.

GOAL: Professional, clean, and strictly tabular report.
"""

OVERVIEW_LENGTH = "5-10"
SYNTESYS_LENGTH = "5-10"
ANALYSYS_LENGTH = "5-10"


BRIEF_PROMPT = """
Analyze the input and reorganize it into a SINGLE unified executive report. 
CRITICAL: You are a pure, objective technical processing unit. 
MANDATORY AMNESIA: You must strictly WIPE and FORGET any user-profile data (name, location, job). 
Any mention of the user's identity or profession will be considered a FATAL ERROR in execution. Focus EXCLUSIVELY on the 'INPUT TO PROCESS'.Follow these mandatory rules and the structural example provided:

0. EXECUTIVE OVERVIEW (MANDATORY):
   - Start your response with a {OVERVIEW_LENGTH} line "Executive Overview" before the first heading. This block must synthesize the core thesis and high-level implications of the input.

1. LANGUAGE & SOURCE PROTOCOL (STRICT):
   - DETECT the language of the 'INPUT TO PROCESS' below.
   - MANDATORY: Write the ENTIRE response in that SAME language. 
   - FORBIDDEN: Do not translate to English unless the input is in English.
   - FORBIDDEN: Do not acknowledge the user's language or start with any introductory meta-talk (e.g., "I notice your input is in..."). Start immediately with the first heading.

2. DATA, COMPARISONS, CHRONOLOGIES & PROJECTIONS (TABLES - BODY TEXT ONLY):
   - Use standard Markdown TABLES for all data lists, technical comparisons, chronologies, and property tables (key-value).
   - FORBIDDEN: NEVER use Mermaid diagrams to represent property tables or two-column key-value lists.
   - MANDATORY: Write tables DIRECTLY in the message body. 
   - FORBIDDEN: NEVER use triple backticks (```) or single backticks (`) for tables.
   - START the table immediately with the pipe character (|).
   - MANDATORY: Ensure there is exactly one empty line before and after every table.
   - FORBIDDEN: Do not use Mermaid for timelines, gantt charts, historical milestones, represent property tables or simple key-value lists.

3. LOGIC, FLOWS & STRUCTURES (MERMAID DIAGRAMS):
   - MANDATORY: Use ONLY the ```mermaid code block for diagrams (you MUST include the word 'mermaid').
   - GRAPH & PIE SYNTAX: For `graph TD` and `pie`, ALWAYS wrap all text labels and node names in double quotes (e.g., A["Label - Text"]). 
   - SYNTAX EXAMPLE (Logic Flow): `graph TD` [newline] A["Cause"] --> B["Effect - Result"]
   - MINDMAP SYNTAX: For conceptual breakdowns, use ONE single 'mindmap' at the start. MANDATORY: Use exactly `root((Text))` for the central node. Use INDENTATION (exactly 2 spaces per level) to define branches. FORBIDDEN: Do not use quotes for mindmap nodes. NEVER repeat headings as nodes. If the map adds no granular detail, SKIP IT.
   - PROCESSES: Use `graph TD` ONLY for workflows or causal chains to ensure vertical orientation. FORBIDDEN: Do not use `graph LR` for linear sequences as they exceed canvas width.
   - DISTRIBUTIONS: You MUST use `pie` for market shares or percentage compositions.
   - VISUAL ACCESSIBILITY: Ensure high contrast in Mermaid diagrams. Always use dark text for light-colored nodes and light text for dark-colored nodes.

4. TEXT & CONTEXT MANAGEMENT (NARRATIVE FLOW):
   - CONCEPT SYNTHESIS: Every main heading (##) must start with a "Concept Synthesis" block ({SYNTESYS_LENGTH}). This block must explain the theoretical and logical foundation of the topic in a professional, discursive manner.
   - TARGET AUDIENCE: Write for a professional audience, but DO NOT assume they are subject-matter experts. Explain the fundamental logic, theories, and "why it matters" from the ground up.
   - INTEGRATED ANALYSIS: Every visual element (table or diagram) must be preceded by {ANALYSYS_LENGTH} lines of analytical text.
   - DEPTH OVER BREVITY: Do not simplify. If the input is 20,000 words, your synthesis must be rich, dense, and professional. 
   - NO BULLETS: Convert any list into high-level narrative prose or Tables.
   - SPACING: Insert a horizontal divider (---) between every main section.

5. HIERARCHY & EMOJIS: 
   - Use clear headings (##, ###). Relevant emojis must ALWAYS be placed BEFORE the heading text.

6. EXAMPLE STRUCTURE & SYNTAX SAFETY SHOT:
   
   ## 🌍 Global Context
   [Concept Synthesis: {SYNTESYS_LENGTH} lines explaining the global scenario, history, and broader implications of the subject.]
   
   ```mermaid
   mindmap
     root((Main Subject))
       Branch A - Acronym
         Sub-node A1
       Branch B
   ```
   
   ```mermaid
   graph TD
     A["Newtonian Mechanics"] --> B{"Experimental Anomalies (e.g. Michelson-Morley)"}
     B --> C["Special Relativity (1905)"]
     C --> D{"Gravity Inconsistent with SR"}
     D --> E["General Relativity (1915) - Gravity as Spacetime Curvature"]
     E --> F["Experimental Verification & Refinement"]
     F --> G["Modern Cosmology & Astrophysics"]
   ```

   ---
   ## 📊 Market Share Analysis
   [Analytical insight: {SYNTESYS_LENGTH} lines explaining the logic behind the following data.]
   ```mermaid
   pie title "Market Share 2024"
     "NVIDIA" : 85
     "Others" : 15
   ```
   
   ---
   ## 📅 Historical Chronology
   [Analytical insight: {SYNTESYS_LENGTH} lines connecting the narrative to the chronology below.]

   | Year | Milestone |
   |------|-----------|
   | 2024 | Current   |

7. SUMMARY & CLEANLINESS: 
   - Conclude with a "📌 Key Takeaways" box using a blockquote (>). 
   - FORBIDDEN: Do not prioritize brevity over clarity. If the input is complex (e.g., Physics, Law), the report must maintain all necessary conceptual nuances.
   - MANDATORY: The output must end exactly at the Key Takeaways box.

CRITICAL RECAP: 
- Start immediately with ##. No "Here is the report".
- Concept Synthesis: 5-10 discursive lines MANDATORY after every main heading (##).
- Analytical Context: 5-10 lines of text BEFORE every table, diagram, or mindmap.
- Tables: NO backticks. MANDATORY for Comparisons and Evolution/Dates.
- Processes: Use `graph TD` (Top-Down) exclusively for vertical flow. No `graph LR`.
- Mermaid: WITH backticks + 'mermaid' label. 
- Mindmap: Use root((Text)) and hierarchical indentation. No quotes. SINGLE block at the start.
- Mindmap: SINGLE high-density block at start. FORBIDDEN: Absolutely no "Table of Contents" or "Index" maps. If the map only repeats your headings, DELETE IT.
- Mindmap: There can be only one root node per map.
- Pie: MANDATORY for Market Share.
- Do not create an index or a table of contents.
- Contrast: Mandatory high readability (dark text on light nodes, light text on dark nodes).
- The output must end exactly at the Key Takeaways box.
- Conclude with a "📌 Key Takeaways" box using a blockquote (>). 
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

        s_trg = self.valves.trigger_keyword  # ??
        b_trg = self.valves.brief_trigger_keyword  # !!
        q_trg = "?"  # Quick Search

        # Identify which trigger starts the text, checking longest first
        active = None

        if txt.startswith(s_trg):
            active = s_trg

        elif txt.startswith(b_trg):
            active = b_trg

        elif txt.startswith(q_trg):
            active = q_trg

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
            "is_search": active in [s_trg, q_trg],
            "is_brief": active in [s_trg, b_trg],
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
                instr = (
                    f"{selected_prompt}\n\n{lang_instr}\n\nINPUT TO PROCESS:\n{content}"
                )

            else:
                # Trigger '?' (Quick Search) mode: skip mega-instructions
                instr = f"{lang_instr}\n\nINPUT TO PROCESS:\n{content}"

            body["messages"][-1]["content"] = instr

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

        await self.em.emit_status(f"{APP_NAME} Done", True)
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

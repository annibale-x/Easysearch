"""
title: EasyBrief - Web Search & Executive Summaries
version: 0.4.5
author: Hannibal
https://github.com/annibale-x/open-webui-easybrief
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: Transform text and web search results into structured Executive Reports with tables and mindmaps using simple triggers (??, >>, v>, t>).
"""

import json
import re
import time
import sys
import httpx  # type: ignore
from typing import Optional, Any, List, Dict, Tuple, Union
from pydantic import BaseModel, Field, validator
from open_webui.main import app  # type: ignore
from open_webui.models.users import Users, UserModel  # type: ignore
from open_webui.utils.chat import generate_chat_completion  # type: ignore

# TODO: Nel schematic brief il prompt tende a buttare sche mi e mindmap in fondo alle tabelle, con contenuti già rappresentati in tabella, biogna dire al modello di privilegiare i diagrammi e non ridondare le tabelle


# --- CONSTANTS ---

APP_ICON = "✨"
APP_NAME = "EasyBrief"
OVERRIDE_WEB_SEARCH = None  # Set to True/False to override user setting
SUPPRESS_OUTPUT = False
EB_WATERMARK = "\u200b\u200b\u200b"  # Invisible watermark (3 Zero Width Spaces)
AUTO_NANO_BRIEF_COMPRESSION = 0.5

# --- MERMAID EXAMPLES (Extracted from source v0.3.7) ---

MERMAID_EXAMPLES = """
4. MERMAID EXAMPLES
   - MANDATORY: Use double quotes for labels.

```mermaid
graph TD
    A["NVIDIA Design"] --> B("TSMC Manufacturing")
    C["SK Hynix/Samsung (HBM/DRAM)"] --> B
    B --> D{"Packaging & Testing (TSMC CoWoS)"}
    D --> E["Distribution (Data Centers/Cloud)"]
    E --> F["End-User Deployment"]
    ...
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
    ...
```

```mermaid
graph TD
    A["Stimulus"] --> B(("CNS Processing"))
    B --> C(("Sympathetic Nervous System"))
    B --> D(("Parasympathetic Nervous System"))
    C --> E["Increased Heart Rate, Dilated Pupils, etc."]
    D --> F["Decreased Heart Rate, Constricted Pupils, etc."]
    E --> G["Response to Stress/Action"]
    F --> H["Rest/Digestion"]
    ...
```

```mermaid
mindmap
  root("Main Subject")
    ("Node")
      ("Sub-Node")
      ("Sub-node (wit parens-enclosed text)")
    ("Node")
      ("Sub-Node")
        ("Sub-Sub-Node")
      ("Sub-Node")
        ("Sub-Sub-Node") 
      ... 
```

```mermaid
pie
  title AI Chip Market Share (2024)
  "NVIDIA" : 95
  "AMD" : 15
  "Intel" : 8
  "Other (ASICs)" : 5
  ...
```
"""

# --- PROMPT TEMPLATES ---

NANO_PROMPT = """
The input is an existing technical report. 
TASK: Distill it into a 'Flash Brief' (max {NANO_LENGTH} words) for quick mobile reading.

1. LANGUAGE PROTOCOL:
   {LANGUAGE_INSTRUCTION}

2. DESTRUCTIVE EDITING:
   - IGNORE all visual syntax (Mermaid, Tables, Code blocks).
   - IGNORE structural boilerplate (Intro, Methodology).

3. OUTPUT FORMAT (Plain Text Only):
   - ### 🎯 **Nano Brief** 
     A single, dense paragraph with the core conclusion.
   - ### ⚡ **Key Concepts** 
     A simple bullet list (max 5 items) extracting key concepts.

4. CONSTRAINT:
   - NO introductory text. NO "Here is the summary". Start immediately with the Thesis.
   - Must use the format defined above
"""

TABLE_PROMPT = """
Analyze the input and reorganize it into a structured executive report.
Follow these mandatory rules:

0. LANGUAGE PROTOCOL:
   {LANGUAGE_INSTRUCTION}

1. DATA & COMPARISONS (TABLES):
   - MANDATORY: Use standard Markdown TABLES for all data lists, time-series, timelines, bullet lists, comparisons, and specs.
   - MANDATORY: Write tables DIRECTLY in the message body. No backticks.
   - FORBIDDEN: NEVER use bullet lists, Mermaid diagrams or any code-based visualization.

2. TEXT & CONTEXT MANAGEMENT:
   - Provide exactly 1-2 lines of introductory context before every table.
   - NO BULLET LISTS: Convert lists of items into Tables.
   - SPACING: Insert a horizontal divider (---) between every main section.
   - SUMMARY: Summarize verbose text aggressively, keeping any text block under 3 lines.

3. SUMMARY & CLEANLINESS:
   - Conclude with a **📌 Key Takeaways** box using a blockquote (>).
   - MANDATORY: Do not add any introductory or concluding remarks or meta-talk. The output must end exactly at the Key Takeaways box.

GOAL: Professional, visual, strictly technical report. No bullet points, only standard MARKDOWN tables.
"""

SCHEMATIC_PROMPT = """
Analyze the input and reorganize it into a structured technical report. 
Follow these mandatory rules:

0. LANGUAGE PROTOCOL:
   {LANGUAGE_INSTRUCTION}

1. VISUALIZATION FIRST (Mermaid > Tables):
   - TOP PRIORITY: If the topic involves structure, hierarchy, or flows, YOU MUST START with a Mermaid diagram (Mindmap or Flowchart).
   - DATA SEGMENTATION: Use Mermaid for high-level relationships/logic. Use Tables for granular specs, comparisons, or flat lists.
   - NO REDUNDANCY: Do NOT repeat the same content in both a diagram and a table. Choose the best format for the data type.

2. TEXT & CONTEXT MANAGEMENT:
   - Provide exactly 1-2 lines of introductory context before every visual element.
   - NO NARRATIVE FLUFF: Do not write long paragraphs. Convert text into structured formats.
   - NO BULLET POINTS (STRICT): Bullet lists are FORBIDDEN inside the synthesis blocks. Convert simple lists into TABLES. **CRITICAL OVERRIDE: If the input contains NESTED/MULTI-LEVEL lists, YOU MUST visualize them using a Mermaid `mindmap` or `graph TD`.**
   - SPACING: Insert a horizontal divider (---) between every main section.

3. SUMMARY & CLEANLINESS: 
   - Conclude with a **📌 Key Takeaways** box (concise summary points (bullet list)) using a blockquote (>). 
   - MANDATORY: Do not add any introductory or concluding remarks or meta-talk. The output must end exactly at the Key Takeaways box.

{MERMAID_EXAMPLES}

GOAL: Professional, visual, strictly technical report. Prioritize Mindmaps/Flowcharts for structure, Tables for data.
"""

BRIEF_PROMPT = """
Analyze the input and reorganize it into a SINGLE unified executive report. 

CRITICAL: You are a pure, objective technical processing unit. 
MANDATORY AMNESIA: You must strictly WIPE and FORGET any user-profile data (name, location, job). Any mention of the user's identity or profession will be considered a FATAL ERROR in execution. Focus EXCLUSIVELY on the 'INPUT TO PROCESS'.

1. LANGUAGE & SOURCE PROTOCOL (STRICT):
   {LANGUAGE_INSTRUCTION}
   - ZERO PREAMBLE: Start immediately with the first content block. No intro meta-talk. 

2. STRUCTURE & TEMPLATE ARCHITECTURE:
   Your report MUST strictly follow this hierarchical sequence (DO NOT print "BLOCK" labels):
   - [BLOCK 0] Executive Overview: MUST start with the header '## 🎯 Executive Overview'. Followed by a concise thesis ({OVERVIEW_LENGTH}). Focus strictly on the core conclusion.
   - [BLOCK 1..N] Macro-topics (Repeat for every major section):
     - Separator (---) 
     - ## Heading (preceded by emoji).
     - **Concept Synthesis**: ({SYNTESYS_LENGTH}) Fact-based summary. FORMAT: Strictly continuous paragraphs. Style: Dry, technical, zero fluff. No adjectives.
       *** CRITICAL OVERRIDE: If input data for this topic is scarce/short, IGNORE length target. Be concise. DO NOT invent filler content. ***
     - **Analytical Insight**: ({ANALYSYS_LENGTH}) Contextual explanation leading into the visual.
     - **Visual Element**: MANDATORY. Insert the most appropriate visual for this section:
       - Use a **TABLE** for data lists, comparisons, specs, or flat chronologies.
       - Use a **MERMAID MINDMAP** (`mindmap`) if the section describes a hierarchy, taxonomy, or complex structure.
       - Use a **MERMAID GRAPH** (`graph TD`) if the section describes a flow or process.
   - [FINAL BLOCK] 📌 Key Takeaways (blockquote >).

3. VISUAL ELEMENT RULES:
   - TABLES: Standard Markdown body text only. NO backticks. Start immediately with the pipe (|). MANDATORY: Exactly one empty line before and after every table.
   - MERMAID GRAPH: MANDATORY: Wrap code in triple backticks (```mermaid). Use `graph TD` exclusively. Use ONLY square brackets `["Text"]` for nodes. ALWAYS wrap text in double quotes.
   - MERMAID PIE: MANDATORY for market shares or percentage distributions. Wrap labels in double quotes.
   - VISUAL ACCESSIBILITY: Ensure high contrast (dark text on light nodes, light text on dark nodes).
   - NARRATIVE PRIORITY (STRICT): **EVERY** visual element (including Mermaid Mindmaps/Graphs) MUST be preceded by `Concept Synthesis` and `Analytical Insight` blocks. NEVER output a 'naked' diagram under a header.
   - NO BULLET POINTS (STRICT): Bullet lists are FORBIDDEN inside the synthesis blocks. Convert simple lists into TABLES. **CRITICAL OVERRIDE: If the input contains NESTED/MULTI-LEVEL lists, YOU MUST visualize them using a Mermaid `mindmap` or `graph TD`.**

{MERMAID_EXAMPLES}

5. REFERENCE TEMPLATE:

---

## 🎯 Executive Overview

A dense {OVERVIEW_LENGTH} words summary.

---

## ⚙️ Foundational Logic

**Concept Synthesis**: {SYNTESYS_LENGTH} words block. Do NOT use bullet points here. Write a dense, factual summary.

**Analytical Insight**: {ANALYSYS_LENGTH} words block explaining the visual below.

```mermaid
graph TD
    A["Main Concept"] --> B["Component"]
```
(OR Table OR Mindmap)

---

📌 **Key Takeaways**
Concise summary points (bullet list).
"""


class ConfigService:
    """Service for handling configuration, valves, and internal state."""

    def __init__(self, ctx):
        """Initialize the ConfigService with context and default model state."""

        self.ctx = ctx
        self.valves, self.user_valves = ctx.valves, ctx.user_valves
        self.start_time = time.time()

        # Helper to construct display triggers based on config
        S = self.valves.search_prefix
        B = self.valves.brief_prefix

        self.model = Store(
            {
                # FIX: Updated to use new prefix-based config
                "search_prefix": f"{S}",
                "brief_prefix": f"{B}",
                "debug": ctx.valves.debug or ctx.user_valves.debug,
                "user_query": "",
                "id": "",
                "original_model": None,
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
        search_prefix: str = Field(
            default="?",
            description="Prefix for Search (e.g. '?'). Double ('??') for Search Only",
            min_length=1,
            max_length=1,
        )
        brief_prefix: str = Field(
            default=">",
            description="Prefix for Brief (e.g. '>'). Double ('>>') for Default Brief.",
            min_length=1,
            max_length=1,
        )
        min_input_threshold: int = Field(
            default=15,
            description="Min word count of input text required to trigger a Brief report (Anti-spam).",
        )
        debug: bool = Field(default=False)

    class UserValves(BaseModel):
        default_brief_mode: str = Field(
            default="brief",
            description="Your personal preference for '>>'. Options: brief, schematic, table, nano.",
        )
        task_model: Optional[str] = Field(
            default=None,
            description="Specific model ID to use for Brief generation.",
        )
        smart_nano_threshold: int = Field(
            default=300,
            description="Auto-switch to Nano Brief if input is shorter than this (prevents fluff). Set 0 to disable.",
        )
        max_nano_brief_length: int = Field(
            default=200,
            ge=50,
            le=500,
            description="Target word count for Nano briefs (Range: 50-500).",
        )
        overview_length: str = Field(
            default="max 100 words",
            description="Target length for Executive Overview (Standard Brief).",
        )
        synthesis_length: str = Field(
            default="max 80 words",
            description="Target length for Concept Synthesis (Standard Brief).",
        )
        analysis_length: str = Field(
            default="max 40 words",
            description="Target length for Analytical Context (Standard Brief).",
        )
        debug: bool = Field(default=False)

        @validator("default_brief_mode")
        def validate_mode(cls, v):
            if v not in ["brief", "schematic", "table", "nano"]:
                raise ValueError("Mode must be: brief, schematic, table, nano")
            return v

    def __init__(self):
        """Initialize the Filter with default valves and state."""

        self.valves, self.user_valves = self.Valves(), self.UserValves()
        self.request = self.debug = self.net = self.em = self.ctx = None
        self.output_content = ""

    def _parse_trigger(self, txt: str) -> Optional[dict]:
        """
        Parse input using Dynamic Trigger Map and Strict Whitespace Separation.
        Syntax: <Trigger>[Modifier] <Whitespace> <Content>
        """

        # 1. Smart I18N Normalization
        smart_map = {
            "»": ">>",
            "«": "<<",
            "—": "-",
            "–": "-",
            "→": "->",
            "←": "<-",
            "？": "?",
            "！": "!",
            "》": ">",
            "：": ":",
        }
        for smart, ascii_val in smart_map.items():
            if txt.startswith(smart):
                txt = txt.replace(smart, ascii_val, 1)
                break

        # 2. Config & Trigger Map Construction
        S = self.valves.search_prefix
        B = self.valves.brief_prefix

        # Core modes mapping ('b' replaces 'r')
        modes = {"n": "nano", "s": "schematic", "t": "table", "b": "brief"}

        trigger_map = {}

        # Generate permutations for modes (Lower & Upper)
        for k, mode in modes.items():
            for char in (k.lower(), k.upper()):
                trigger_map[f"{char}{B}"] = {"s": False, "b": True, "mode": mode}
                trigger_map[f"{S}{char}"] = {"s": True, "b": True, "mode": mode}

        # Explicit overrides for Double-Tap (High Priority)
        trigger_map.update(
            {
                f"{B}{B}": {"s": False, "b": True, "mode": None},  # Default Brief
                f"{S}{S}": {"s": True, "b": False, "mode": None},  # Search Only
                f"{S}{B}": {
                    "s": True,
                    "b": True,
                    "mode": None,
                },  # Search + Default Brief
            }
        )

        # 3. Robust Tokenization (Unix-Style)
        parts = txt.split(maxsplit=1)

        if not parts:
            return None

        command_token = parts[0]

        if len(command_token) < 2:
            return None

        prefix_2 = command_token[:2]
        matched_cfg = trigger_map.get(prefix_2)

        if not matched_cfg:
            return None

        # 4. Extract Modifier (Strict Syntax)
        raw_mod = command_token[2:]
        lang = None

        if raw_mod:
            # Strict Check: Modifiers MUST start with ':'
            if not raw_mod.startswith(":"):
                return None

            clean_mod = raw_mod[1:]
            if clean_mod:
                lang = clean_mod

        # 5. Extract Content
        content = parts[1].strip() if len(parts) > 1 else ""

        return {
            "is_search": matched_cfg["s"],
            "is_brief": matched_cfg["b"],
            "target_mode": matched_cfg["mode"],
            "lang": lang,
            "content": content,
        }

    async def _extract_query(
        self, text: str, model: str, user_id: str, target_lang: str = None
    ) -> str:
        """Helper to extract a search query. Adapts language based on user modifier."""
        try:
            user = Users.get_user_by_id(user_id)
            if not user:
                return text[:100]  # Fallback

            # Logic: If user requested a specific language (e.g. ?>en), force query in that language.
            if target_lang:
                lang_instr = f"MANDATORY: Output the query strictly in {target_lang.upper()}. IGNORE the input language."
            else:
                lang_instr = (
                    "MANDATORY: Keep the query in the SAME language as the input text."
                )

            messages = [
                {
                    "role": "system",
                    "content": f"You are a Search Query Generator. Output ONLY a single, effective Google search query based on the user text. {lang_instr} Do NOT explain.",
                },
                {"role": "user", "content": text[:2000]},
            ]

            form_data = {"model": model, "messages": messages, "stream": False}

            response = await generate_chat_completion(
                self.request, form_data, user=user
            )

            if isinstance(response, dict) and "choices" in response:
                return response["choices"][0]["message"]["content"].strip().strip('"')

            return text[:100]

        except Exception as e:
            if self.debug:
                self.debug.log(f"Query Gen Failed: {e}", True)
            return text[:100]

    async def inlet(
        self,
        body: dict,
        __user__: dict = None,  # type: ignore
        __event_emitter__: callable = None,  # type: ignore
        __request__=None,
    ) -> dict:
        """Process the incoming request and trigger filter logic."""

        self.ctx = None

        # Phase 0: Early User Config Load (Required for Dynamic Triggers)
        self.request = __request__
        uv_data = __user__.get("valves", {}) if __user__ else {}
        self.user_valves = (
            self.UserValves(**uv_data) if isinstance(uv_data, dict) else uv_data
        )

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
        self.ctx = ConfigService(self)
        self.debug, self.em = (
            DebugService(self),
            EmitterService(__event_emitter__, self),
        )

        await self.em.emit_status("🚀 EasyBrief Started", False)

        # Phase 3: State Management
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )
        self.ctx.model.forced_language = parsed["lang"]

        # FIX: Save brief state for outlet decision
        self.ctx.model.is_brief = parsed["is_brief"]

        content = parsed["content"]

        # Handle Contextual/Empty Triggers
        if not content and len(msg_list) > 1:
            prev_content = msg_list[-2].get("content", "")
            content = (
                prev_content[0].get("text", "")
                if isinstance(prev_content, list)
                else str(prev_content)
            )

            if EB_WATERMARK in content:
                self.debug.log("🌊 Recursive Brief detected: Input contains Watermark.")

            self.debug.log(f"Empty trigger detected. Using context: {content[:50]}...")

            # CRITICAL FIX: Extract Search Query if search is requested on context
            if parsed["is_search"]:
                await self.em.emit_status("⛏️ Extracting Search Query..", False)
                # Pass parsed["lang"] to force query translation if needed
                content = await self._extract_query(
                    content, body.get("model"), __user__["id"], parsed["lang"]
                )
                self.debug.log(f"Extracted Query: {content}")
                await self.em.emit_status(f"🔍 Searching: {content[:60]}...", False)

        # Check Minimum Input Threshold (Renamed from min_brief_words)
        # Managed by Admin Valves
        min_threshold = self.valves.min_input_threshold

        if (
            parsed["is_brief"]
            and not parsed["is_search"]
            and len(content.split()) < min_threshold
        ):
            self.debug.log(
                f"Skipping Brief: content too short ({len(content.split())} < {min_threshold} words)."
            )
            await self.em.emit_status("💬 Input too short for Brief", True)

            if body["messages"]:
                body["messages"][-1]["content"] = content

            return body

        self.ctx.model.user_query, self.ctx.model.id = content, body.get("model")

        try:
            # Apply Web Search Override logic
            self.ctx.model.override_web_search = parsed["is_search"]

            # PREPARE LANGUAGE INSTRUCTION (Robust Logic)
            if parsed["lang"]:
                target_lang = parsed["lang"].upper()
                lang_instruction = (
                    f"- IGNORE input language. TARGET LANGUAGE IS {target_lang}.\n"
                    f"   - TRANSLATION: You MUST translate the content into {target_lang}.\n"
                    f"   - MANDATORY: Write the ENTIRE response in {target_lang}."
                )
            else:
                # FIX: Remove negative logic ("FORBIDDEN") which confuses 12B models.
                # Use positive reinforcement for English retention.
                lang_instruction = (
                    "- DETECT the language of the '=== INPUT TO PROCESS ===' below.\n"
                    "- MANDATORY: Respond in the EXACT SAME language as the detected input.\n"
                    "- CRITICAL: If the input is in English, you MUST respond in English."
                )

            # Decision Logic: Quick Search vs Briefing
            if parsed["is_brief"]:

                # Check if a specific task model is requested via UserValves
                target_model = self.user_valves.task_model
                current_model = body.get("model")

                if target_model and target_model != current_model:
                    self.debug.log(f"Swapping model: {current_model} -> {target_model}")
                    self.ctx.model.original_model = current_model
                    body["model"] = target_model

                # SMART NANO LOGIC (Absolute Threshold per User Request)
                # Calculate word count of the actual input (Cleaning <think> blocks)
                clean_content = re.sub(
                    r"<think>.*?</think>", "", content, flags=re.DOTALL
                ).strip()
                input_words = len(clean_content.split())
                smart_threshold = self.user_valves.smart_nano_threshold

                # State variables
                user_wants_nano = False
                explicit_mode = parsed[
                    "target_mode"
                ]  # rich, schematic, table, nano, or None

                # Resolve Modes
                if explicit_mode == "nano":
                    user_wants_nano = True
                elif EB_WATERMARK in content:
                    user_wants_nano = True

                # Logic: Smart switch only if mode is None (implicit >>) AND text is short
                force_smart_nano = (
                    not parsed["is_search"]
                    and input_words < smart_threshold
                    and smart_threshold > 0
                    and explicit_mode is None
                    and not user_wants_nano
                )

                if user_wants_nano or force_smart_nano:

                    # Calculate Dynamic Length
                    # If forced by smart logic, use 70% of input length to stay tight
                    if force_smart_nano:
                        calc_len = int(input_words * AUTO_NANO_BRIEF_COMPRESSION)
                        target_len = max(50, calc_len)
                        await self.em.emit_status(
                            f"💬 Input too short ({input_words}w)"
                        )
                        status_msg = f"✨ Falling back to Nano Brief ({target_len}w).."
                    else:
                        target_len = self.user_valves.max_nano_brief_length
                        status_msg = "✨ Generating a Nano Brief.."

                    self.debug.log(
                        f"Nano Mode Active. Forced: {force_smart_nano}. Target Words: {target_len}"
                    )

                    selected_prompt = NANO_PROMPT.format(
                        NANO_LENGTH=target_len, LANGUAGE_INSTRUCTION=lang_instruction
                    )
                    await self.em.emit_status(status_msg, False)

                else:
                    # 2. Rich/Schematic/Table Mode

                    # Resolve Final Mode (Default Fallback)
                    final_mode = explicit_mode
                    if final_mode is None:
                        final_mode = self.user_valves.default_brief_mode

                    # Select Prompt
                    if final_mode == "schematic":
                        base_prompt = SCHEMATIC_PROMPT.format(
                            MERMAID_EXAMPLES=MERMAID_EXAMPLES,
                            LANGUAGE_INSTRUCTION=lang_instruction,
                        )
                        status_label = "Schematic Brief"
                    elif final_mode == "table":
                        base_prompt = TABLE_PROMPT.format(
                            LANGUAGE_INSTRUCTION=lang_instruction
                        )
                        status_label = "Table Brief"
                    else:
                        # Standard Brief (Default)
                        base_prompt = BRIEF_PROMPT.format(
                            OVERVIEW_LENGTH=self.user_valves.overview_length,
                            SYNTESYS_LENGTH=self.user_valves.synthesis_length,
                            ANALYSYS_LENGTH=self.user_valves.analysis_length,
                            LANGUAGE_INSTRUCTION=lang_instruction,
                            MERMAID_EXAMPLES=MERMAID_EXAMPLES,
                        )
                        status_label = "Standard Brief"

                    await self.em.emit_status(
                        f"✨ Generating a {status_label}..", False
                    )

                    selected_prompt = base_prompt

                data_content = (
                    f"Search Query: {content}" if parsed["is_search"] else content
                )

                # Fallback instruction for small models if no lang specified
                fallback_instr = ""
                if not parsed["lang"]:
                    fallback_instr = "If ambiguous or mixed, default to ENGLISH."

                instr = (
                    f"{selected_prompt}\n\n"
                    f"=== INPUT TO PROCESS ===\n"
                    f"{data_content}\n"
                    f"=== END INPUT TO PROCESS ===\n\n"
                    f"{fallback_instr}"
                )

            else:
                # Trigger '??' (Quick Search) mode
                simple_lang_instr = (
                    f"*** REQUIRED OUTPUT LANGUAGE: {parsed['lang'].upper()} ***"
                    if parsed["lang"]
                    else "DETECT and match the input language."
                )
                instr = (
                    f"Search Query: {content}\n\n"
                    f"INSTRUCTION: Answer the query above using ONLY the provided search results/context. "
                    f"Do not hallucinate or use prior conversation memory if unrelated.\n\n"
                    f"{simple_lang_instr}"
                )

            body["messages"][-1]["content"] = instr

            # We must wipe history for:
            # 1. Briefs (>>) -> Always fresh analysis
            # 2. Explicit Search (?? query) -> Prevent context bleeding/hallucination from previous turns
            # We ONLY keep history if it's a Contextual Search (?? without query) acting on previous msg
            is_explicit_search = parsed["is_search"] and len(content.strip()) > 0

            if parsed["is_brief"] or is_explicit_search:
                # Standard Isolation: Keep only the current instruction
                current_instr = body["messages"][-1]["content"]
                body["messages"] = [{"role": "user", "content": current_instr}]
                self.debug.log("History wiped: Isolation Mode active.")

            if self.ctx.model.override_web_search is not None:
                if "features" not in body:
                    body["features"] = {}
                body["features"]["web_search"] = self.ctx.model.override_web_search

            self.ctx.model.executed = True
            self.debug.log(
                f"Execution Mode: {'Search' if parsed['is_search'] else 'Brief'} | Briefing: {parsed['is_brief']} | Lang: {parsed['lang'] or 'Auto'}"
            )

        except Exception as e:
            await self.debug.error(e)

        return self._suppress_output(body)

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None  # type: ignore
    ) -> dict:
        """Process the outgoing response and restore web search state."""

        if self.ctx and self.ctx.model.executed:

            # Apply invisible watermark to identify EB outputs in future turns
            if (
                self.ctx.model.is_brief
                and "messages" in body
                and len(body["messages"]) > 0
            ):
                body["messages"][-1]["content"] += EB_WATERMARK

            # Restore original model if it was swapped
            if self.ctx.model.original_model:
                body["model"] = self.ctx.model.original_model

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
            st_icon = "🎯" if self.ctx.model.is_brief else "🔍"
            await self.em.emit_status(f"{st_icon} {APP_NAME} Done", True)

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

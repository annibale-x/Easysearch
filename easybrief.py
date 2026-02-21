"""
title: EasyBrief - Web Search & Executive Summaries
version: 0.4.8
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

# --- SHARED RULES (BUILDING BLOCKS) ---

# 1. Formatting & Protocol
MOD_IDENTITY = """
CRITICAL: You are a pure, objective technical processing unit. 
MANDATORY AMNESIA: You must strictly WIPE and FORGET any user-profile data. Focus EXCLUSIVELY on the 'INPUT TO PROCESS'.
"""

MOD_FORMATTING_CORE = """
- **META-TALK**: MANDATORY: Do not add any introductory or concluding remarks (e.g., "Here is the report").
- **HEADERS**: Use H2 (##) for main sections. NO H1.
- **SPACING**: Insert a horizontal divider (---) between every main section.
"""

# 2. Visual Engine: Tables
RULE_TABLES = """
*STRICT TABLE RULES*:
- **FORMAT**: Write **RAW** Markdown (start lines with `|`).
- **FORBIDDEN**: Do NOT wrap tables in backticks or code blocks.
- **USAGE**: Use tables for all flat lists, data, time-series, and specs.
- **NO BULLETS**: Convert lists of items into Tables.
"""

# 3. Visual Engine: Mermaid (Legacy Bluff)
RULE_MERMAID = """
*MERMAID COMPATIBILITY MODE (CRITICAL)*:
- **TARGET RENDERER**: Legacy Mermaid Engine.
- **CAPABILITIES**: Supports ONLY basic nodes and arrows.
- **UNSUPPORTED FEATURES (WILL CRASH)**: `subgraph`, `style`, `fill`, `linkStyle`, `classDef`.
- **STRATEGY**: Use simple `graph TD` flowcharts without nesting.
- **SYNTAX**: Always use double quotes for labels: `id["Text"]`.
- **MANDATORY**: Wrap code in triple backticks (```mermaid).
"""

# 4. Closing Standard
MOD_TAKEAWAYS = """
CLOSING (Use this EXACT format, max 8 points):
> **📌 Key Takeaways**
> * **Label 1**: Point 1
> * **Label 2**: Point 2
> ...

- MANDATORY: The header "**Key Takeaways**" must be BOLD. The bullet points must be on separate lines inside the blockquote.
- END exactly at the Key Takeaways box.
"""

# --- MERMAID EXAMPLES ---

MERMAID_EXAMPLES = """
5. MERMAID SYNTAX REFERENCE (STRICTLY v8.0 COMPATIBLE):
   - SYSTEM CONSTRAINT: The renderer is OLD. It DOES NOT support `subgraph`, `style`, `linkStyle`, or `fill`.
   - USE ONLY: `graph TD`, `graph LR`, `mindmap`.
   - QUOTES: Mandatory for all labels. `id["Label"]`.

   CORRECT PATTERNS:
    ```mermaid
    graph TD
      A["Concept A"] --> B["Concept B"]
      B -- "Connection" --> C["Concept C"]
      ...  
    ```
    ```mermaid
    graph LR
        A["Root Cause"] --> B("Process A (Standard)")
        A --> C(("Process B (Critical)"))
        A --> D("Process C (Secondary)")
        B -- "Condition 1, High Impact" --> E{"Systemic Result"}
        C -- "Condition 2" --> E
        D -- "Condition 3" --> E
        E --> F["Final Outcome (Long-term effects)"]
        B <--> C
        B <--> D
        C <--> D
        ...
    ```
    ```mermaid
    graph TD
        A["Main System"] 
            -->|Type 1| B["Sub-System A"]
            -->|Type 1| E["Sub-System B"]
            -->|Type 2| F["Sub-System C"]
            -->|Type 2| G["Sub-System D"]
        B --> D["Component A1"]
        B --> E["Component A2"]
        ...
    ```

    CORRECT PIE:
    ```mermaid
    pie
      title "Generic Market Distribution"
      "Category A" : 70
      "Category B" : 20
      "Category C" : 5
      "Others" : 5
      ...
    ```

   CORRECT MINDMAP:
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
"""

# --- PROMPT TEMPLATES ---

# Uses: MOD_TAKEAWAYS
NANO_PROMPT = f"""
The input is an existing technical report. 
TASK: Distill it into a 'Flash Brief' (max {{NANO_LENGTH}} words) for quick mobile reading.

1. LANGUAGE PROTOCOL:
   {{LANGUAGE_INSTRUCTION}}

2. DESTRUCTIVE EDITING:
   - IGNORE all visual syntax (Mermaid, Tables, Code blocks).
   - IGNORE structural boilerplate (Intro, Methodology).

3. OUTPUT FORMAT (Plain Text Only):
   - **## 🎯 Nano Brief** 
     A single, dense paragraph with the core conclusion. Start immediately.

   {MOD_TAKEAWAYS}

4. CONSTRAINT:
   - NO introductory text. NO "Here is the summary".
   - Must use the format defined above.
"""

# Uses: MOD_FORMATTING_CORE, RULE_TABLES, MOD_TAKEAWAYS
TABLE_PROMPT = f"""
Analyze the input and reorganize it into a structured executive report.

0. LANGUAGE PROTOCOL:
   {{LANGUAGE_INSTRUCTION}}

1. REPORT STRUCTURE:
   - **## 🎯 Executive Overview**
     (Mandatory New Line): Write a concise thesis (3-5 lines) summarizing the data trends or core findings.
     (Constraint): Normal text only (No Bold/Headers).

2. DATA & COMPARISONS (TABLES):
   {RULE_TABLES}
   - FORBIDDEN: NEVER use bullet lists, Mermaid diagrams or any code-based visualization.

3. NARRATIVE FLOW (CRITICAL):
   - **PRE-TABLE INSIGHT**: Mandatory. Write a specific **Analytical Insight** (2-3 lines) *BEFORE* every table.
     - *Bad:* "The following table shows the data."
     - *Good:* "The data reveals a critical shift in X, driven primarily by Y factors listed below."
   - **POST-TABLE**: **FORBIDDEN**. Do NOT write summaries or remarks *after* the table. Move strictly to the divider (---).
   {MOD_FORMATTING_CORE}

4. CLOSING:
   {MOD_TAKEAWAYS}

GOAL: Professional, visual, strictly technical report. Insight -> Table -> Next Section.
"""

# Uses: MOD_FORMATTING_CORE, RULE_TABLES, RULE_MERMAID, MOD_TAKEAWAYS
SCHEMATIC_PROMPT = f"""
Analyze the input and reorganize it into a structured technical report.

0. LANGUAGE PROTOCOL:
   {{LANGUAGE_INSTRUCTION}}

1. REPORT STRUCTURE (STRICT FLOW):
   - **## 🎯 Executive Overview**
     (Mandatory New Line): Write a concise thesis (3-5 lines).
     (Constraint): Normal text only (No Bold/Headers).

   - **## <Emoji> Section Header**
     (Repeat for each main topic).

   - **Analytical Context**
     Write a brief paragraph (2-3 lines) explaining the logic *BEFORE* the visual.

   - **[VISUAL CONTENT]**
     Insert the Visual Element immediately here.
     *STRICT FORMATTING RULES*:
     - **IF TABLE**: Write **RAW** Markdown (start lines with `|`). **FORBIDDEN**: Backticks/Code blocks.
     - **IF MERMAID**: MUST wrap in triple backticks (```mermaid).
     - **ALL**: Do NOT print labels like "Figure 1:" or "Table A:".

2. VISUALIZATION STRATEGY (Mermaid > Tables):
   - **HIERARCHY**: Use `mermaid` (Mindmap or Graph).
   - **DATA**: Use Tables for flat lists/specs.
   - **NO REDUNDANCY**: Do not repeat diagram content in tables.
   {MOD_FORMATTING_CORE}

3. VISUAL ENGINE RULES:
   {RULE_MERMAID}
   {RULE_TABLES}

4. CLOSING:
   {MOD_TAKEAWAYS}

{{MERMAID_EXAMPLES}}

GOAL: Visual-first technical report. Flow: Overview -> Header -> Context -> Visual.
"""

# Uses: MOD_IDENTITY, RULE_TABLES, RULE_MERMAID, MOD_TAKEAWAYS
BRIEF_PROMPT = f"""
Analyze the input and reorganize it into a SINGLE unified executive report. 

{MOD_IDENTITY}

1. LANGUAGE & SOURCE PROTOCOL (STRICT):
   {{LANGUAGE_INSTRUCTION}}
   - ZERO PREAMBLE: Start immediately with the first content block. No intro meta-talk. 

2. STRUCTURE & TEMPLATE ARCHITECTURE:
   Your report MUST strictly follow this hierarchical sequence (DO NOT print "BLOCK" labels):
   - [BLOCK 0] Executive Overview: MUST start with the header '## 🎯 Executive Overview'. Followed by a concise thesis ({{OVERVIEW_LENGTH}}). Focus strictly on the core conclusion.
   - [BLOCK 1..N] Macro-topics (Repeat for every major section):
     - Separator (---) 
     - ## Heading (preceded by emoji).
     - **Concept Synthesis**: ({{SYNTESYS_LENGTH}}) Fact-based summary. FORMAT: Strictly continuous paragraphs. Style: Dry, technical, zero fluff. No adjectives.
       *** CRITICAL OVERRIDE: If input data for this topic is scarce/short, IGNORE length target. Be concise. DO NOT invent filler content. ***
     - **Analytical Insight**: ({{ANALYSYS_LENGTH}}) Contextual explanation leading into the visual.
     - **Visual Element**: MANDATORY. Insert the most appropriate visual for this section:
       - Use a **TABLE** for data lists, comparisons, specs, or flat chronologies.
       - Use a **MERMAID MINDMAP** (`mindmap`) if the section describes a hierarchy, taxonomy, or complex structure.
       - Use a **MERMAID GRAPH** (`graph TD`) if the section describes a flow or process.
   - [FINAL BLOCK] 📌 Key Takeaways (blockquote >).

3. VISUAL ELEMENT RULES:
   - VISUAL ACCESSIBILITY: Ensure high contrast (dark text on light nodes, light text on dark nodes).
   - NARRATIVE PRIORITY (STRICT): **EVERY** visual element (including Mermaid Mindmaps/Graphs) MUST be preceded by `Concept Synthesis` and `Analytical Insight` blocks. NEVER output a 'naked' diagram under a header.
   - NO BULLET POINTS (STRICT): Bullet lists are FORBIDDEN inside the synthesis blocks. Convert simple lists into TABLES. **CRITICAL OVERRIDE: If the input contains NESTED/MULTI-LEVEL lists, YOU MUST visualize them using a Mermaid `mindmap` or `graph TD`.**
   {RULE_TABLES}
   {RULE_MERMAID}

{{MERMAID_EXAMPLES}}

5. REFERENCE TEMPLATE:

---

## 🎯 Executive Overview

A dense {{OVERVIEW_LENGTH}} words summary.

---

## ⚙️ Foundational Logic

**Concept Synthesis**: {{SYNTESYS_LENGTH}} words block. Do NOT use bullet points here. Write a dense, factual summary.

**Analytical Insight**: {{ANALYSYS_LENGTH}} words block explaining the visual below.

```mermaid
graph TD
    A["Main Concept"] --> B["Component"]
```
(OR Table OR Mindmap)

---

6. CLOSING:
   {MOD_TAKEAWAYS}
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

    def _get_language_instruction(self, lang_code: Optional[str]) -> str:
        """Generate the language instruction string."""
        if lang_code:
            target_lang = lang_code.upper()
            return (
                f"- IGNORE input language. TARGET LANGUAGE IS {target_lang}.\n"
                f"   - TRANSLATION: You MUST translate the content into {target_lang}.\n"
                f"   - MANDATORY: Write the ENTIRE response in {target_lang}."
            )
        else:
            return (
                "- DETECT the language of the '=== INPUT TO PROCESS ===' below.\n"
                "- MANDATORY: Respond in the EXACT SAME language as the detected input.\n"
                "- CRITICAL: If the input is in English, you MUST respond in English."
            )

    def _resolve_brief_mode(
        self, content: str, parsed: dict
    ) -> Tuple[str, Optional[int], str]:
        """
        Determine the specific Brief Mode (Nano vs Standard vs Table etc) based on:
        1. Explicit User Request (e.g. n>)
        2. Content Length (Smart Threshold)
        3. Watermark detection (Recursive)
        """
        # Calculate word count (Cleaning <think> blocks)
        clean_content = re.sub(
            r"<think>.*?</think>", "", content, flags=re.DOTALL
        ).strip()
        input_words = len(clean_content.split())
        smart_threshold = self.user_valves.smart_nano_threshold

        # Logic Variables
        explicit_mode = parsed["target_mode"]  # nano, schematic, table, brief, or None
        user_wants_nano = explicit_mode == "nano" or EB_WATERMARK in content

        # Auto-switch Logic: implicit mode (>>) AND text is short AND threshold enabled
        force_smart_nano = (
            not parsed["is_search"]
            and input_words < smart_threshold
            and smart_threshold > 0
            and explicit_mode is None
            and not user_wants_nano
        )

        if user_wants_nano or force_smart_nano:
            # Determine length target for Nano
            if force_smart_nano:
                calc_len = int(input_words * AUTO_NANO_BRIEF_COMPRESSION)
                target_len = max(50, calc_len)
                status_msg = f"✨ Falling back to Nano Brief ({target_len}w).."
                self.debug.log(
                    f"Smart Nano Active: Input {input_words}w < Threshold {smart_threshold}w"
                )
            else:
                target_len = self.user_valves.max_nano_brief_length
                status_msg = "✨ Generating a Nano Brief.."

            return "nano", target_len, status_msg

        # Fallback to standard/configured modes
        final_mode = explicit_mode
        if final_mode is None:
            final_mode = self.user_valves.default_brief_mode

        # Map labels
        labels = {
            "schematic": "Schematic Brief",
            "table": "Table Brief",
            "brief": "Standard Brief",
        }
        label = labels.get(final_mode, "Standard Brief")

        return final_mode, None, f"✨ Generating a {label}.."

    def _get_prompt_template(
        self, mode: str, target_len: Optional[int], lang_instr: str
    ) -> str:
        """Select and format the correct prompt template based on mode."""
        if mode == "nano":
            return NANO_PROMPT.format(
                NANO_LENGTH=target_len, LANGUAGE_INSTRUCTION=lang_instr
            )

        elif mode == "schematic":
            return SCHEMATIC_PROMPT.format(
                MERMAID_EXAMPLES=MERMAID_EXAMPLES,
                LANGUAGE_INSTRUCTION=lang_instr,
            )

        elif mode == "table":
            return TABLE_PROMPT.format(LANGUAGE_INSTRUCTION=lang_instr)

        else:
            # Standard Brief
            return BRIEF_PROMPT.format(
                OVERVIEW_LENGTH=self.user_valves.overview_length,
                SYNTESYS_LENGTH=self.user_valves.synthesis_length,
                ANALYSYS_LENGTH=self.user_valves.analysis_length,
                LANGUAGE_INSTRUCTION=lang_instruction,
                MERMAID_EXAMPLES=MERMAID_EXAMPLES,
            )

    def _construct_final_message(
        self, prompt: str, content: str, is_search: bool, lang_code: Optional[str]
    ) -> str:
        """Assemble the final message string sent to the model."""
        data_content = f"Search Query: {content}" if is_search else content
        fallback_instr = (
            "If ambiguous or mixed, default to ENGLISH." if not lang_code else ""
        )

        return (
            f"{prompt}\n\n"
            f"=== INPUT TO PROCESS ===\n"
            f"{data_content}\n"
            f"=== END INPUT TO PROCESS ===\n\n"
            f"{fallback_instr}"
        )

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
        self.ctx.model.is_brief = parsed["is_brief"]

        content = parsed["content"]

        # Phase 4: Context Resolution
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

            if parsed["is_search"]:
                await self.em.emit_status("⛏️ Extracting Search Query..", False)
                content = await self._extract_query(
                    content, body.get("model"), __user__["id"], parsed["lang"]
                )
                self.debug.log(f"Extracted Query: {content}")
                await self.em.emit_status(f"🔍 Searching: {content[:60]}...", False)

        # Phase 5: Threshold Check (Anti-Spam)
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
            # Phase 6: Model Configuration
            self.ctx.model.override_web_search = parsed["is_search"]
            lang_instruction = self._get_language_instruction(parsed["lang"])

            if parsed["is_brief"]:
                # Model Swapping Logic
                target_model = self.user_valves.task_model
                current_model = body.get("model")
                if target_model and target_model != current_model:
                    self.debug.log(f"Swapping model: {current_model} -> {target_model}")
                    self.ctx.model.original_model = current_model
                    body["model"] = target_model

                # Brief Generation Logic (Modularized)
                mode, target_len, status_msg = self._resolve_brief_mode(content, parsed)
                await self.em.emit_status(status_msg, False)

                selected_prompt = self._get_prompt_template(
                    mode, target_len, lang_instruction
                )
                instr = self._construct_final_message(
                    selected_prompt, content, parsed["is_search"], parsed["lang"]
                )

            else:
                # Search Only Logic (??)
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

            # Phase 7: Apply History & Features
            body["messages"][-1]["content"] = instr
            is_explicit_search = parsed["is_search"] and len(parsed["content"]) > 0

            if parsed["is_brief"] or is_explicit_search:
                current_instr = body["messages"][-1]["content"]
                body["messages"] = [{"role": "user", "content": current_instr}]
                self.debug.log("History wiped: Isolation Mode active.")

            if self.ctx.model.override_web_search is not None:
                if "features" not in body:
                    body["features"] = {}
                body["features"]["web_search"] = self.ctx.model.override_web_search

            self.ctx.model.executed = True
            self.debug.log(
                f"Execution Mode: {'Search' if parsed['is_search'] else 'Brief'} | Lang: {parsed['lang'] or 'Auto'}"
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
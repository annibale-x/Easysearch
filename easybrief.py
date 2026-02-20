"""
title: EasyBrief - Web Search & Executive Summaries
version: 0.4.4
author: Hannibal
https://github.com/annibale-x/open-webui-easybrief
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: Transform text, web searches, and attached documents into structured Executive Reports with tables and mindmaps using simple triggers (??, >>, s>, t>).
"""

import json
import re
import time
import sys
import os
import httpx  # type: ignore
from typing import Optional, Any, List, Dict, Tuple, Union
from pydantic import BaseModel, Field, validator
from open_webui.main import app  # type: ignore
from open_webui.models.users import Users, UserModel  # type: ignore
from open_webui.utils.chat import generate_chat_completion  # type: ignore

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
   - NO BULLET LISTS: Convert lists of items into Tables or Mindmaps.
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

1.5 BRIEF DENSITY (STRICT):
   - You must use minimum 1500 words    

2. STRUCTURE & TEMPLATE ARCHITECTURE:
   Your report MUST strictly follow this hierarchical sequence (DO NOT print "BLOCK" labels):
   - [BLOCK 0] Executive Overview: MUST start with the header '## 🎯 Executive Overview'. Followed by a concise thesis ({OVERVIEW_LENGTH}). Focus strictly on the core conclusion.
   - [BLOCK 0.5] Structural Visual: CONDITIONAL. Insert a MERMAID CODE BLOCK (```mermaid) containing a `mindmap` ONLY IF the topic involves complex structural relationships (systems, taxonomies). OMIT this block for simple rankings, flat lists, or linear chronologies.
   - [BLOCK 1..N] Macro-topics:
     - Separator (---) 
     - ## Heading (preceded by emoji).
     - Concept Synthesis ({SYNTESYS_LENGTH}): Fact-based summary. FORMAT: Strictly continuous paragraphs. Style: Dry, technical, zero fluff. No adjectives.
       *** CRITICAL OVERRIDE: If input data for this topic is scarce/short, IGNORE length target. Be concise. DO NOT invent filler content. ***
     - [Optional Data Block]: Analytical Context ({ANALYSYS_LENGTH}) followed by its Visual Element (Table OR Pie Chart, Mindmap or Graph).
   - [FINAL BLOCK] 📌 Key Takeaways (blockquote >).

3. VISUAL ELEMENT RULES:
   - TABLES: Standard Markdown body text only. NO backticks. Start immediately with the pipe (|). MANDATORY: Exactly one empty line before and after every table.
   - MERMAID GRAPH: MANDATORY: Wrap code in triple backticks (```mermaid). Use `graph TD` exclusively. Use ONLY square brackets `["Text"]` for nodes. ALWAYS wrap text in double quotes.
   - MERMAID PIE: MANDATORY for market shares or percentage distributions. Wrap labels in double quotes.
   - VISUAL ACCESSIBILITY: Ensure high contrast (dark text on light nodes, light text on dark nodes).
   - NARRATIVE PRIORITY: Every visual element MUST be preceded by its own Analytical Context block.
   - NO BULLET POINTS (STRICT): Bullet lists are FORBIDDEN inside the synthesis blocks. Convert simple lists into TABLES. For multi-level/nested lists, YOU MUST split them into specific Sub-headings (###) containing their own dedicated Tables.


{MERMAID_EXAMPLES}

5. REFERENCE TEMPLATE:

---

## 🎯 Executive Overview

A dense {OVERVIEW_LENGTH} words summary.

```mermaid
graph TD
    A["Main Concept"] --> B["Component"]
```

---

## ⚙️ Foundational Logic

**Concept Synthesis**: {SYNTESYS_LENGTH} words block. Do NOT use bullet points here. Write a dense, factual summary.

**Analytical Insight**: {ANALYSYS_LENGTH} words block.

| Dimension | Impact |
|-----------|--------|
| Logic A   | High   |

---

📌 **Key Takeaways**
Concise summary points (bullet list).

---

CRITICAL RECAP: 
- Flow: Overview -> Visual -> Heading -> Synthesis (Must be {SYNTESYS_LENGTH}, NO BULLETS) -> Analysis -> Table/Graph.
- Respond ONLY in the input language (No English translation).
- Tables: NO backticks. Pipe (|) start. One empty line before/after.
- The output must end exactly at the Key Takeaways box.
- No bullets: Convert lists of items into Tables.
- Use 🎯 as emoji in the overview.
- Use 📌 as emoji in the Key Takeaways.
- Must use the format of REFERENCE TEMPLATE defined above
"""


class FileService:
    """Service to handle direct file reading and text extraction."""

    def __init__(self, debug_service):
        self.debug = debug_service

    def extract_text(self, file_path: str, content_type: str) -> str:
        """Determines the file type and extracts text accordingly."""
        if not os.path.exists(file_path):
            self.debug.log(f"File not found at path: {file_path}", True)
            return ""

        try:
            if "pdf" in content_type:
                return self._read_pdf(file_path)
            elif "word" in content_type or "docx" in content_type:
                return self._read_docx(file_path)
            else:
                # Default to text/plain
                return self._read_text(file_path)
        except Exception as e:
            self.debug.log(f"Extraction failed for {file_path}: {str(e)}", True)
            return ""

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            self.debug.log(f"Text read error: {e}", True)
            return ""

    def _read_pdf(self, path: str) -> str:
        text_content = []
        try:
            import pypdf  # type: ignore

            reader = pypdf.PdfReader(path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_content.append(f"--- PAGE {i+1} ---\n{text}")

                # Basic check for images (heuristic)
                if "/XObject" in page.get("/Resources", {}):
                    text_content.append(
                        "\n[SYSTEM NOTE: Page contains visual elements/images not extracted]\n"
                    )

            return "\n".join(text_content)
        except ImportError:
            self.debug.log("pypdf library not found. Falling back to raw text.", True)
            return self._read_text(path)
        except Exception as e:
            self.debug.log(f"PDF read error: {e}", True)
            return ""

    def _read_docx(self, path: str) -> str:
        text_content = []
        try:
            import docx  # type: ignore

            doc = docx.Document(path)
            for para in doc.paragraphs:
                if para.text:
                    text_content.append(para.text)

            # Extract Tables from DOCX
            for table in doc.tables:
                text_content.append("\n[DOCX TABLE DATA]:")
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    text_content.append(" | ".join(row_data))
                text_content.append("\n")

            return "\n".join(text_content)
        except ImportError:
            self.debug.log(
                "python-docx library not found. Falling back to raw text.", True
            )
            return self._read_text(path)
        except Exception as e:
            self.debug.log(f"DOCX read error: {e}", True)
            return ""


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
            default="rich",
            description="Your personal preference for '>>'. Options: rich, schematic, table, nano.",
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
            description="Target length for Executive Overview (Rich Brief).",
        )
        synthesis_length: str = Field(
            default="max 80 words",
            description="Target length for Concept Synthesis (Rich Brief).",
        )
        analysis_length: str = Field(
            default="max 40 words",
            description="Target length for Analytical Context (Rich Brief).",
        )
        debug: bool = Field(default=False)

        @validator("default_brief_mode")
        def validate_mode(cls, v):
            if v not in ["rich", "schematic", "table", "nano"]:
                raise ValueError("Mode must be: rich, schematic, table, nano")
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

        # Core modes mapping
        modes = {"n": "nano", "s": "schematic", "t": "table", "r": "rich"}

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

    def _get_capabilities(self, model_id: str) -> dict:
        """Retrieve model capabilities from the global application state."""
        default_caps = {"vision": False, "file_context": False}

        if not self.request or not hasattr(self.request.app.state, "MODELS"):
            return default_caps

        try:
            models = self.request.app.state.MODELS
            if model_id in models:
                # Based on the user dump structure
                meta = models[model_id].get("info", {}).get("meta", {})
                caps = meta.get("capabilities", {})
                return {
                    "vision": caps.get("vision", False),
                    "file_context": caps.get("file_context", False),
                }
        except Exception as e:
            if self.debug:
                self.debug.log(f"Capability Check Error: {e}", True)

        return default_caps

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

        # Phase 0: Early User Config Load
        self.request = __request__
        uv_data = __user__.get("valves", {}) if __user__ else {}
        self.user_valves = (
            self.UserValves(**uv_data) if isinstance(uv_data, dict) else uv_data
        )

        msg_list = body.get("messages", [])
        if not msg_list:
            return body

        # Phase 1: Robust Attachment Detection
        last_msg_obj = msg_list[-1]
        msg_files = last_msg_obj.get("files", []) or last_msg_obj.get("images", [])

        root_files = body.get("files", [])
        meta_files = body.get("metadata", {}).get("files", [])

        has_attachments = len(msg_files) > 0

        # Phase 2: Trigger Parsing
        last_msg_content = last_msg_obj.get("content", "")
        txt = (
            last_msg_content[0].get("text", "")
            if isinstance(last_msg_content, list)
            else str(last_msg_content)
        ).strip()

        parsed = self._parse_trigger(txt)

        if not parsed:
            return body

        # Phase 3: Initialization
        self.output_content = ""
        self.ctx = ConfigService(self)
        self.debug, self.em = (
            DebugService(self),
            EmitterService(__event_emitter__, self),
        )
        self.files = FileService(self.debug)

        await self.em.emit_status("🚀 EasyBrief Started", False)

        if has_attachments:
            self.debug.log(
                f"📎 Attachments detected! (Msg: {len(msg_files)}, Root: {len(root_files)}, Meta: {len(meta_files)})"
            )

        # Phase 4: State Management
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )
        self.ctx.model.forced_language = parsed["lang"]
        self.ctx.model.is_brief = parsed["is_brief"]

        content = parsed["content"]

        # Extraction Logic (RAG Bypass)
        extracted_context = ""
        if has_attachments:
            self.debug.log(f"📎 Files detected. Starting Direct Injection...")
            await self.em.emit_status("📂 Reading files directly..", False)

            full_text = []
            processed_paths = set()

            # Combine all sources
            all_files = msg_files

            for f in all_files:
                f_data = f.get("file", {})
                f_path = f_data.get("path")

                if f_path and f_path not in processed_paths:
                    processed_paths.add(f_path)
                    f_type = f_data.get("meta", {}).get("content_type", "")

                    text = self.files.extract_text(f_path, f_type)
                    if text:
                        full_text.append(
                            f"\n=== FILE: {f_data.get('name', 'Unknown')} ===\n{text}"
                        )

            if full_text:
                extracted_context = "\n".join(full_text)

                # --- DEBUG AUDIT START ---
                # Calcola e stampa le metriche reali dell'input
                word_count = len(extracted_context.split())
                self.debug.log(
                    f"📄 INPUT SIZE: {len(extracted_context)} chars | ~{word_count} words"
                )

                # Stampa l'inizio e la fine per verificare che il file sia completo
                preview_len = 500
                head = extracted_context[:preview_len].replace("\n", " ")
                tail = extracted_context[-preview_len:].replace("\n", " ")
                self.debug.log(f"📄 HEAD: {head}...")
                self.debug.log(f"📄 TAIL: ...{tail}")
                # --- DEBUG AUDIT END ---

                self.debug.log(
                    f"Extracted {len(extracted_context)} chars. Disabling RAG."
                )

                # CRITICAL: Nuke file keys to bypass RAG
                if "files" in body:
                    del body["files"]
                if "files" in last_msg_obj:
                    del last_msg_obj["files"]
                if "metadata" in body and "files" in body["metadata"]:
                    del body["metadata"]["files"]

        # Handle Contextual/Empty Triggers
        if not content and not has_attachments and len(msg_list) > 1:
            prev_content = msg_list[-2].get("content", "")
            content = (
                prev_content[0].get("text", "")
                if isinstance(prev_content, list)
                else str(prev_content)
            )

            if EB_WATERMARK in content:
                self.debug.log("🌊 Recursive Brief detected: Input contains Watermark.")

            if parsed["is_search"]:
                await self.em.emit_status("⛏️ Extracting Search Query..", False)
                content = await self._extract_query(
                    content, body.get("model"), __user__["id"], parsed["lang"]
                )
                self.debug.log(f"Extracted Query: {content}")
                await self.em.emit_status(f"🔍 Searching: {content[:60]}...", False)

        # Minimum Input Threshold
        min_threshold = self.valves.min_input_threshold
        if (
            parsed["is_brief"]
            and not parsed["is_search"]
            and not extracted_context
            and len(content.split()) < min_threshold
        ):
            self.debug.log(f"Skipping Brief: content too short.")
            await self.em.emit_status("💬 Input too short for Brief", True)
            if body["messages"]:
                body["messages"][-1]["content"] = content
            return body

        self.ctx.model.user_query, self.ctx.model.id = content, body.get("model")

        try:
            # Apply Web Search Override
            self.ctx.model.override_web_search = parsed["is_search"]

            # PREPARE LANGUAGE INSTRUCTION
            if parsed["lang"]:
                target_lang = parsed["lang"].upper()
                lang_instruction = (
                    f"- IGNORE input language. TARGET LANGUAGE IS {target_lang}.\n"
                    f"   - TRANSLATION: You MUST translate the content into {target_lang}.\n"
                    f"   - MANDATORY: Write the ENTIRE response in {target_lang}."
                )
            else:
                lang_instruction = (
                    "- DETECT the language of the '=== INPUT TO PROCESS ===' below.\n"
                    "- MANDATORY: Respond in the EXACT SAME language as the detected input.\n"
                    "- CRITICAL: If the input is in English, you MUST respond in English."
                )

            # --- DECISION LOGIC ---
            if parsed["is_brief"]:

                # Task Model Swap
                target_model = self.user_valves.task_model
                current_model = body.get("model")
                if target_model and target_model != current_model:
                    self.debug.log(f"Swapping model: {current_model} -> {target_model}")
                    self.ctx.model.original_model = current_model
                    body["model"] = target_model

                # Smart Nano Logic
                clean_content = re.sub(
                    r"<think>.*?</think>", "", content, flags=re.DOTALL
                ).strip()
                input_words = len(clean_content.split())
                smart_threshold = self.user_valves.smart_nano_threshold

                user_wants_nano = (
                    parsed["target_mode"] == "nano" or EB_WATERMARK in content
                )

                # Disable Smart Nano if files are attached
                force_smart_nano = (
                    not parsed["is_search"]
                    and not extracted_context
                    and input_words < smart_threshold
                    and smart_threshold > 0
                    and parsed["target_mode"] is None
                    and not user_wants_nano
                )

                # DYNAMIC LENGTHS
                ov_len = self.user_valves.overview_length
                syn_len = self.user_valves.synthesis_length
                ana_len = self.user_valves.analysis_length

                if extracted_context:
                    ov_len = "comprehensive executive summary (300-500 words)"
                    syn_len = "detailed breakdown (no word limit, extract key data)"
                    ana_len = "in-depth technical analysis"
                    if user_wants_nano:
                        user_wants_nano = False
                        parsed["target_mode"] = "rich"

                if user_wants_nano or force_smart_nano:
                    # NANO MODE
                    if force_smart_nano:
                        calc_len = int(input_words * AUTO_NANO_BRIEF_COMPRESSION)
                        target_len = max(50, calc_len)
                        await self.em.emit_status(
                            f"💬 Input too short. Auto-Nano ({target_len}w).."
                        )
                    else:
                        target_len = self.user_valves.max_nano_brief_length
                        await self.em.emit_status("✨ Generating a Nano Brief..")

                    selected_prompt = NANO_PROMPT.format(
                        NANO_LENGTH=target_len, LANGUAGE_INSTRUCTION=lang_instruction
                    )
                else:
                    # RICH / SCHEMATIC / TABLE MODE
                    final_mode = (
                        parsed["target_mode"] or self.user_valves.default_brief_mode
                    )
                    if final_mode == "simple":
                        final_mode = "table"

                    if final_mode == "schematic":
                        base_prompt = SCHEMATIC_PROMPT
                        status_label = "Schematic Brief"
                    elif final_mode == "table":
                        base_prompt = TABLE_PROMPT
                        status_label = "Table Brief"
                    else:
                        base_prompt = BRIEF_PROMPT
                        status_label = "Rich Brief"

                    # Format the prompt
                    if final_mode == "rich":
                        selected_prompt = base_prompt.format(
                            OVERVIEW_LENGTH=ov_len,
                            SYNTESYS_LENGTH=syn_len,
                            ANALYSYS_LENGTH=ana_len,
                            LANGUAGE_INSTRUCTION=lang_instruction,
                            MERMAID_EXAMPLES=MERMAID_EXAMPLES,
                        )
                    elif final_mode == "schematic":
                        selected_prompt = base_prompt.format(
                            MERMAID_EXAMPLES=MERMAID_EXAMPLES,
                            LANGUAGE_INSTRUCTION=lang_instruction,
                        )
                    else:
                        selected_prompt = base_prompt.format(
                            LANGUAGE_INSTRUCTION=lang_instruction
                        )

                    await self.em.emit_status(
                        f"✨ Generating a {status_label}..", False
                    )

                # --- PROMPT INJECTION (Split Strategy) ---

                fallback_instr = ""
                if not parsed["lang"]:
                    fallback_instr = (
                        "If ambiguous, detect language from the input text below."
                    )

                if extracted_context:
                    # [FIX v0.5.6] REINFORCEMENT LEARNING FOR LARGE DOCS
                    # 1. System: The Laws (Template & Rules)
                    system_payload = (
                        f"ROLE: Executive Analyst.\n{selected_prompt}\n{fallback_instr}"
                    )

                    # 2. User: The Data + The Sandwich (Reminder at the end)
                    doc_lang_reinforcement = (
                        f"MANDATORY: Respond in {parsed['lang'].upper()}."
                        if parsed["lang"]
                        else "MANDATORY: Detect the language of the document above and RESPOND IN THE SAME LANGUAGE."
                    )

                    user_payload = (
                        f"=== INPUT DOCUMENT ===\n{extracted_context}\n=== END INPUT ===\n\n"
                        f"⚠️ FINAL INSTRUCTION - ADHERENCE CHECK ⚠️\n"
                        f"1. {doc_lang_reinforcement}\n"
                        f"2. You MUST follow the structure defined in the System Prompt (Overview -> Mermaid -> Synthesis).\n"
                        f"3. STRICTLY NO BULLET LISTS: Use Markdown TABLES for all lists.\n"
                        f'4. MERMAID SYNTAX: Always use double quotes for labels (e.g. A["Label"]).\n'
                        f"\n{MERMAID_EXAMPLES}"  # Reinject examples for context retention
                    )

                    instr = f"{system_payload}\n\n{user_payload}"  # Legacy fallback
                else:
                    input_header = "=== INPUT TO PROCESS ==="
                    instr = (
                        f"{selected_prompt}\n\n"
                        f"{input_header}\n"
                        f"{content}\n"
                        f"=== END INPUT ===\n\n"
                        f"{fallback_instr}"
                    )
                    system_payload = None

            else:
                # [SEARCH MODE] ('??')
                simple_lang_instr = (
                    f"*** REQUIRED OUTPUT LANGUAGE: {parsed['lang'].upper()} ***"
                    if parsed["lang"]
                    else "DETECT and match the input language."
                )
                instr = (
                    f"Search Query: {content}\n\n"
                    f"INSTRUCTION: Answer the query above using ONLY the provided search results/context. "
                    f"Do not hallucinate.\n\n"
                    f"{simple_lang_instr}"
                )
                system_payload = None

            body["messages"][-1]["content"] = instr

            # --- ISOLATION LOGIC ---
            is_explicit_search = parsed["is_search"] and len(content.strip()) > 0

            if parsed["is_brief"] or is_explicit_search:
                if parsed["is_brief"] and system_payload:
                    # [FIX v0.5.5] Use explicit System Role for strict adherence
                    body["messages"] = [
                        {"role": "system", "content": system_payload},
                        {"role": "user", "content": user_payload},
                    ]
                    self.debug.log("History wiped: System+User split active.")
                else:
                    body["messages"] = [{"role": "user", "content": instr}]
                    self.debug.log("Text Mode: History wiped.")

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

"""
title: EasyBrief - Web Search & Executive Summaries
version: 0.5.1
author: Hannibal
https://github.com/annibale-x/open-webui-easybrief
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: Transform text and web search results into structured Executive Reports with tables and mindmaps using simple triggers (??, >>, v>, t>).
"""

import os
import json
import re
import time
import sys
import datetime
import asyncio
from typing import Optional, Any, List, Dict, Tuple, Union
from pydantic import BaseModel, Field, validator
from open_webui.main import app  # type: ignore
from open_webui.models.users import Users, UserModel  # type: ignore
from open_webui.utils.chat import generate_chat_completion  # type: ignore
from open_webui.routers.retrieval import SearchForm, process_web_search  # type: ignore

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from lxml import html as lxml_html

    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False


# --- CONSTANTS ---

APP_ICON = "✨"
APP_NAME = "EasyBrief"
OVERRIDE_WEB_SEARCH = None  # Set to True/False to override user setting
AUTO_NANO_BRIEF_COMPRESSION = 0.5
MAX_CHARS_PER_WEB_RESULT = 8000
TRACE = False

# --- CONSTANTS & TEMPLATES (MODULAR REFACTOR) ---

# DEBUG OVERRIDE: Set True to bypass all logic and use the template below
DEBUG_PROMPT_OVERRIDE = False
DEBUG_PROMPT_TEMPLATE = """
[SYSTEM]
Role: Debugger.
Task: Say HELLO WORLD 😁.
"""

# Standard Executive Summary Block
SUMMARY_BLOCK_TEMPLATE = """Start your output with:
## 🎯 Executive Summary
(Use EXACTLY this header with the 🎯 emoji).
Write a dense summary  here. Target length: {LENGTH}.
Aim for maximum information density within the target length.
"""

MOD_TAKEAWAYS = f"""
End your response with only one text block. Use exactly this template (you MUST use the 📌 emoji):
### 📌 Key Takeaways
> - Your label: Description.
> - Your label: Description.
---
Closing rules:
- NO other text after ---
- Bold **Your label** with **
- Up to 8 bullets
"""

DEFAULT_REPEAT_RULE = "Analyze each Main Topic found in text:"

# --- WEB SEARCH HANDLER (PORTABLE MODULE) ---

QUERY_GENERATION_TEMPLATE = """### Task:
Analyze the user request to determine the necessity of generating search queries.
The aim is to retrieve comprehensive, updated, and valuable information.

### Guidelines:
- Respond **EXCLUSIVELY** with a JSON object. Any form of extra commentary is strictly prohibited.
- Format: {{ "queries": ["query1", "query2"] }}
- Generate up to {COUNT} distinct, concise, and relevant queries.
- Today's date is: {DATE}.

### User Request:
{REQUEST}

### Output:
Strictly return in JSON format:
{{
  "queries": ["query1", "query2"]
}}
"""

# --- VISUAL ASSETS (MODULAR RULES) ---

VISUAL_ASSETS = {
    "table": {
        "rule": "IF comparative data (rows/cols) exists → USE Markdown Table. ELSE skip.",
        "syntax": """**Tables**:
    RULES:
    1. Only MARKDOWN tables.
    2. Align columns strictly.
    3. Follow EXACTLY the syntax of the following example:
| YOUR HEADING | YOUR HEADING |
|--------------|--------------|
| YOUR DATA    | YOUR DATA    |
    """,
    },
    "mindmap": {
        "rule": "IF hierarchical structure (root->branch->leaf) exists → USE Mermaid mindmap. ELSE skip.",
        "syntax": """**Mindmaps**: Mermaid `mindmap`.
    RULES:
    1. Only one root node can exist, e.g., `root((Root node description))`.
    2. Every node except the root MUST be indented with exactly two spaces of indentation. Each subsequent hierarchical level must add exactly two additional spaces (4, 6, 8, etc.).
    3. Use a descriptive label for each line.
    4. Use parentheses ONLY to define node shapes.
    5. NO brackets of any kind (), [], {} are allowed INSIDE the text of the label itself; replace them with double quotes (") if needed.
    6. If a label violates ANY rule, fix it immediately before printing.
    7. Always specify the code-block type: ```mermaid.
    8. Follow EXACTLY the syntax of the following example:
```mermaid
mindmap
  root((Model))
    Problems
      Fragile syntax
      "No brackets in labels"
    Solutions
      Very specific prompt
      Rigid system prompt
```
    9. MENTALLY verify that the mindmap you are about to print strictly adheres to the previous 8 rules. If they are not all satisfied, mentally re-run the mindmap generation for (max 10 times) until all rules are met.
    """,
    },
    "graph": {
        "rule": "IF sequential process/flow/decision exists → USE Mermaid graph TD. ELSE skip.",
        "syntax": """**Flowcharts**: Mermaid `graph TD`.
    RULES:
    1. Nodes Syntax: `ID("Text")`, `ID["Text"]`, `ID{"Text"}`.
    2 Connectors Label EXACT Syntax: `|"Label"|` (use pipes before and after the label text)
    3 Connectors Syntax: `ID1 -->|"Label"| ID2` (No spaces between pipes and arrows).
    4. Logic: No dead ends. All negative paths must loop back to a previous check or start.
    5. No trailing characters after brackets: `ID["Text"]` is correct, `ID["Text"])` is a failure.
    6. Always specify the code-block type: ```mermaid.
    7. Follow EXACTLY the syntax and logic structure of the provided one-shot:
```mermaid
graph TD
    A("Process Start") -->|"Initialize"| B{"Validation"}
    B -->|"Invalid?"| C["Wait / Retry"]
    C -->|"Re-check"| B
    B -->|"Valid?"| D["Core Execution!"]
    D --> E{"Integrity Check"}
    E -->|"Critical Error"| F["System Reset"]
    F --> A
    E -->|"Success"| G("End: Goal Reached")
```
    8. MENTALLY verify that the graph TD you are about to print strictly adheres to the previous 7 rules. If they are not all satisfied, mentally re-run the mindmap generation for maximum 10 times until all rules are met.
    """,
    },
    "pie": {
        # Rafforziamo la regola di selezione iniziale
        "rule": "IF data represents parts of a whole (e.g. Market Share) → USE Mermaid pie. ELSE skip.",
        "syntax": """**Pie Charts**: Mermaid `pie`.
    RULES:
    1. MANDATORY CHECK: Does the data represent a "Market Share" or "Distribution"? If NOT, output nothing for this visual section.
    2. CRITICAL: NO percentage symbol `%`. Use ONLY raw numbers (e.g. `"Label" : 40`).
    3. CRITICAL: NO parentheses `()` in title.
    4. Always specify the code-block type: ```mermaid.
    5. Follow EXACTLY the syntax of the provided one-shot:
```mermaid
pie
    title Key Distribution
    "Category A" : 40
    "Category B" : 35
    "Category C" : 25
```
    6. MENTALLY VERIFY: If the data does not strictly fit these rules, DO NOT generate the chart.
    """,
    },
}

# Configuration for each mode (Refactored for Modular Visuals)
PROMPT_CONFIG = {
    "nano": {
        "action": "Compress text into a Flash Brief.",
        "structure": "## 🎯 Nano Brief\n(Single dense paragraph of {LENGTH}).",
        "visuals": [],  # No visuals
        "repeat_rule": "NANO BRIEF CONTENT:",
        "example_header": "## 🎯 Nano Brief\n[Content...]",
    },
    "table": {
        "action": "Reorganize text into a Structured Report.",
        "structure": "## [EMOJI] [TOPIC TITLE]\n**Insight**: (2-3 sentences).\n**Visual**: Raw Markdown Table ONLY.",
        "visuals": ["table"],
        "example_header": """## [YOUR EMOJI HERE] [WRITE YOUR TOPIC HERE..]
**Insight**: [Analysis...]""",
    },
    "schematic": {
        "action": "Reorganize text into a Visual Technical Report.",
        "structure": "## [EMOJI] [TOPIC TITLE]\n**Context**: (1 sentence).\n**Visual**: Mermaid Mindmap OR Graph TD.",
        "visuals": ["mindmap", "graph"],
        "example_header": """## [YOUR EMOJI HERE] [WRITE YOUR TOPIC HERE..]
**Context**: [Context...]""",
    },
    "brief": {
        "action": "Generate a Structured Executive Report.",
        "structure": "## [EMOJI] [TOPIC TITLE]\n**Concept Synthesis**: ({{SYNTESYS_LENGTH}}).\n**Analytical Insight**: ({{ANALYSYS_LENGTH}}).\n**Visual**: Select the best format from the ALLOWED list below.",
        "visuals": ["table", "mindmap", "pie", "graph"],
        "repeat_rule": DEFAULT_REPEAT_RULE,
        "example_header": """## [YOUR EMOJI HERE] [WRITE YOUR TOPIC HERE..]
**Concept Synthesis**: [Text...]
**Analytical Insight**: [Text...]""",
    },
    # Fallback for compact models (Graph removed)
    "simple_brief": {
        "action": "Generate a Structured Executive Report.",
        "structure": "## [EMOJI] [TOPIC TITLE]\n**Concept Synthesis**: ({{SYNTESYS_LENGTH}}).\n**Analytical Insight**: ({{ANALYSYS_LENGTH}}).\n**Visual**: Select the best format from the ALLOWED list below.",
        "visuals": ["table", "mindmap", "pie"],  # Graph removed for stability
        "repeat_rule": DEFAULT_REPEAT_RULE,
        "example_header": """## [YOUR EMOJI HERE] [WRITE YOUR TOPIC HERE..]
**Concept Synthesis**: [Text...]
**Analytical Insight**: [Text...]""",
    },
}

# The Base Template (Modular Version)
MASTER_PROMPT = f"""
[SYSTEM]
Role: Analyst. Task: {{ACTION_TYPE}}
Mode: Silent.
[LANGUAGE]
{{LANGUAGE_INSTRUCTION}}
[STRUCTURE]
{{SUMMARY_BLOCK}}
---
{{REPEAT_RULE}}
---
{{STRUCTURE_BLOCK}}
[CLOSING]
{MOD_TAKEAWAYS}
[VISUALS]
**Status**:
ALLOWED: {{ALLOWED_VISUALS_LIST}}
**Guidelines**:
{{VISUAL_GUIDELINES}}
{{VISUAL_SYNTAX}}
[TEMPLATE]
{{EXAMPLE_BLOCK}}
"""


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


class ShadowRequest:
    """
    A thread-safe proxy for the Request object.
    It intercepts access to app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER
    without modifying the global singleton state.
    """

    def __init__(self, original_request, override_bypass: bool):
        self._req = original_request
        self._override_bypass = override_bypass

        # 3. Config Proxy
        class ConfigProxy:
            def __init__(self, real_config, bypass_val):
                self._real = real_config
                self._bypass = bypass_val

            def __getattr__(self, name):
                if name == "BYPASS_WEB_SEARCH_WEB_LOADER":
                    return self._bypass
                return getattr(self._real, name)

        # 2. State Proxy
        class StateProxy:
            def __init__(self, real_state, config_proxy):
                self._real = real_state
                self.config = config_proxy

            def __getattr__(self, name):
                if name == "config":
                    return self.config
                return getattr(self._real, name)

        # 1. App Proxy
        class AppProxy:
            def __init__(self, real_app, state_proxy):
                self._real = real_app
                self.state = state_proxy

            def __getattr__(self, name):
                if name == "state":
                    return self.state
                return getattr(self._real, name)

        # Build the nested proxy structure
        real_app = original_request.app
        real_state = real_app.state
        real_config = real_state.config

        self.app = AppProxy(
            real_app, StateProxy(real_state, ConfigProxy(real_config, override_bypass))
        )

    def __getattr__(self, name):
        # Delegate everything else to the real request
        if name == "app":
            return self.app
        return getattr(self._req, name)


class WebSearchHandler:
    """
    A portable handler for Web Search operations in Open WebUI Filters.
    Encapsulates query generation, execution, citation emission, and result formatting.
    """

    def __init__(
        self,
        request,
        user_id: str,
        emitter: Any,
        debug_service: Any = None,
    ):
        self.request = request
        self.user_id = user_id
        self.em = emitter
        self.debug = debug_service
        self.user_obj = Users.get_user_by_id(user_id)

    def log(self, msg: str, is_error: bool = False):
        if self.debug:
            self.debug.log(f"[WebSearchHandler] {msg}", is_error)

    async def search(
        self, query: str, model: str, max_queries: int = 3
    ) -> Optional[str]:
        """
        Main entry point: Generates queries, executes search, emits citations, returns formatted context.
        Returns None if search fails or yields no results.
        """
        try:
            # 1. Generate Queries
            await self.em.emit_status("Generating Search Queries", False)
            queries = await self._generate_queries(query, model, max_queries)
            if not queries:
                queries = [query]  # Fallback
            self.log(f"Generated Queries: {queries}")
            await self.em.emit_search_queries(queries)

            # 2. Execute Search (Bypassing OWUI Loader safely)
            results = await self._execute_search(queries)

            if self.debug and TRACE:
                self.debug.dump(results, "RAW SEARCH RESULTS")

            if not results:
                await self.em.emit_status("⚠️ No results found", True)
                return None

            # 3. Process Results (Parallel Fetch + LXML + Heuristics)
            formatted_context = await self._process_results(results)

            if TRACE:
                self.debug.log(f"Formatted results: {formatted_context}")
            return formatted_context

        except Exception as e:
            self.log(f"Search Cycle Failed: {e}", True)
            await self.em.emit_status(f"❌ Search Error: {str(e)}", True)
            return None

    async def _generate_queries(self, text: str, model: str, count: int) -> List[str]:
        """Uses LLM to expand the user request into multiple search queries."""
        try:
            prompt = QUERY_GENERATION_TEMPLATE.format(
                COUNT=count, DATE=datetime.date.today(), REQUEST=text
            )
            messages = [{"role": "user", "content": prompt}]
            form_data = {"model": model, "messages": messages, "stream": False}

            # Call LLM
            response = await generate_chat_completion(
                self.request, form_data, user=self.user_obj
            )

            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"].strip()
                # Clean markdown
                content = re.sub(r"```json|```", "", content).strip()
                try:
                    data = json.loads(content)
                    queries = data.get("queries", [])
                    if isinstance(queries, list):
                        return queries[:count]
                except json.JSONDecodeError:
                    self.log("JSON Decode Error in Query Gen", True)
                    # Fallback parsing
                    return [
                        line.strip('- *"')
                        for line in content.split("\n")
                        if line.strip()
                    ][:count]
            return [text]
        except Exception as e:
            self.log(f"Query Gen Error: {e}", True)
            return [text]

    async def _execute_search(self, queries: List[str]) -> Any:
        """Calls Open WebUI search using a Shadow Request to safely bypass the loader."""
        try:
            # Create a thread-safe proxy request that lies about the config
            # This prevents Race Conditions on the global app.state
            shadow_req = ShadowRequest(self.request, override_bypass=True)

            form_data = SearchForm(queries=queries, collection_name="")

            # Pass the shadow request instead of the real one
            return await process_web_search(shadow_req, form_data, self.user_obj)
        except Exception as e:
            self.log(f"Process Web Search Error: {e}", True)
            raise e

    async def _fetch_concurrently(self, urls: List[str]) -> Dict[str, str]:
        """Fetches multiple URLs in parallel using HTTPX, respecting Proxy and SSL settings."""
        if not HTTPX_AVAILABLE or not urls:
            return {}

        results = {}
        # Detect Custom CA Bundle (for corporate/self-signed certs)
        verify_ssl = os.environ.get("REQUESTS_CA_BUNDLE", True)
        if verify_ssl == "":
            verify_ssl = True

        timeout = httpx.Timeout(8.0, connect=5.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            # trust_env=True reads HTTP_PROXY/HTTPS_PROXY automatically
            async with httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers=headers,
                follow_redirects=True,
                verify=verify_ssl,
                trust_env=True,
            ) as client:

                tasks = []
                for url in urls:
                    tasks.append(client.get(url))

                # Execute parallel fetch
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for url, resp in zip(urls, responses):
                    if isinstance(resp, httpx.Response) and resp.status_code == 200:
                        results[url] = resp.text
                    elif self.debug and isinstance(resp, Exception):
                        self.debug.log(f"Fetch failed for {url}: {resp}")

        except Exception as e:
            self.log(f"HTTPX Batch Error: {e}", True)

        return results

    def _clean_with_lxml(self, raw_html: str) -> str:
        """
        Uses lxml to strip HTML tags, scripts, styles, and structural noise.
        Much more robust than Regex.
        """
        if not raw_html or not LXML_AVAILABLE:
            return ""

        try:
            # Parse HTML
            tree = lxml_html.fromstring(raw_html)

            # Remove noise elements (scripts, styles, nav, footer, etc.)
            cleaner_xpath = "//script | //style | //nav | //footer | //header | //aside | //form | //iframe | //noscript | //div[contains(@class, 'menu')] | //div[contains(@class, 'footer')]"
            for element in tree.xpath(cleaner_xpath):
                element.drop_tree()

            # Extract text content
            text = tree.text_content()
            return text.strip()
        except Exception:
            return ""

    async def _process_results(self, results: Any) -> Optional[str]:
        """Parses results, fetches raw HTML in parallel, and builds context."""
        if not isinstance(results, dict) or "items" not in results:
            return None

        items = results["items"]
        # Note: 'docs' will be empty/useless because we bypassed the loader!

        if not items:
            return None

        await self.em.emit_status(f"Found {len(items)} sources", False)

        # 1. Emit Citations & Collect URLs
        urls_to_fetch = []
        for item in items:
            url = item.get("link", "")
            if url:
                urls_to_fetch.append(url)
            await self.em.emit_citation(
                item.get("title", "Source"), item.get("snippet", ""), url
            )

        # 2. Parallel Fetch (The Turbo Boost)
        fetched_html_map = {}
        if HTTPX_AVAILABLE and LXML_AVAILABLE and urls_to_fetch:
            await self.em.emit_status(f"Deep reading {len(urls_to_fetch)} pages", False)
            fetched_html_map = await self._fetch_concurrently(urls_to_fetch)

        # 3. Build Context
        context_parts = []

        # Expanded Noise Pattern (Compiled once for performance)
        noise_pattern = re.compile(
            r"^(?:menu|home|search|sign in|log in|sign up|register|subscribe|newsletter|account|profile|cart|checkout|buy now|shop|close|cancel|skip to content|next|previous|back to top|privacy policy|terms|cookie|copyright|all rights reserved|legal|contact us|help|support|faq|social|follow us|share|facebook|twitter|instagram|linkedin|youtube|advertisement|sponsored|promoted|related posts|read more|loading|posted by|written by|author|category|tags)$",
            re.IGNORECASE,
        )

        for i, item in enumerate(items):
            url = item.get("link", "")
            title = item.get("title", "Source")
            text = ""

            # STRATEGY A: High-Quality LXML (From our parallel fetch)
            if url in fetched_html_map:
                text = self._clean_with_lxml(fetched_html_map[url])

            # STRATEGY B: Fallback to Snippet (Since we bypassed OWUI loader, we only have snippets as backup)
            if not text:
                text = item.get("snippet", "")

            # 4. CLEANING PIPELINE (Universal Polish)
            # Applied to ALL text sources (LXML or Fallback) for maximum purity.

            # A. Basic Normalization
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = re.sub(r"[ \t\u00A0]+", " ", text)  # Collapse horizontal whitespace

            # B. Line-by-Line Filtering
            lines = text.split("\n")
            cleaned_lines = []
            prev_line = ""

            for line in lines:
                line = line.strip()

                # Filter 1: Empty lines
                if not line:
                    continue

                # Filter 2: Exact Noise Match (Case Insensitive)
                if noise_pattern.match(line):
                    continue

                # Filter 3: Short structural junk (e.g., "|", ">>", "---", "•")
                # Removes lines < 5 chars that contain NO alphanumeric characters
                if len(line) < 5 and not any(c.isalnum() for c in line):
                    continue

                # Filter 4: Date/Time clutter (heuristic)
                # Removes lines that are just dates like "Oct 12, 2023" or "12/10/2023"
                if len(line) < 20 and re.match(
                    r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3} \d{1,2},? \d{4}", line
                ):
                    continue

                # Filter 5: Consecutive Deduplication
                if line == prev_line:
                    continue

                cleaned_lines.append(line)
                prev_line = line

            text = "\n".join(cleaned_lines)

            # C. Collapse multiple newlines (3+ becomes 2)
            text = re.sub(r"\n{3,}", "\n\n", text)

            # 3. Truncate
            if len(text) > MAX_CHARS_PER_WEB_RESULT:
                text = text[:MAX_CHARS_PER_WEB_RESULT] + "... [TRUNCATED]"

            context_parts.append(
                f"--- Source {i+1}: {title} ---\nURL: {url}\nContent:\n{text}\n"
            )

        return "\n".join(context_parts)


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

    async def emit_search_queries(self, queries: List[str]):
        """Emit search queries to trigger the native UI pills."""
        if self.emitter:
            await self.emitter(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search_queries_generated",
                        "description": "🔍 Searching",
                        "queries": queries,
                        "done": False,
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
        summary_length: str = Field(  # RENAMED from overview_length
            default="max 100 words",
            description="Target length for Summary Overview.",
        )
        synthesis_length: str = Field(
            default="max 80 words",
            description="Target length for Concept Synthesis.",
        )
        analysis_length: str = Field(
            default="max 40 words",
            description="Target length for Analytical Context.",
        )
        max_search_queries: int = Field(
            default=3,
            ge=1,
            le=10,
            description="Max number of parallel search queries to generate for broader coverage.",
        )
        temperature: float = Field(
            default=0.15,
            ge=0.0,
            le=1.0,
            description="Creativity control (Lower = More precise syntax). Default: 0.15",
        )
        top_p: float = Field(
            default=0.8,
            ge=0.1,
            le=1.0,
            description="Vocabulary filter (Lower = More focused). Default: 0.8",
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
                # Local Brief: n>
                trigger_map[f"{char}{B}"] = {"s": False, "b": True, "mode": mode}
                # Web Brief (Sandwich): ?n>
                trigger_map[f"{S}{char}{B}"] = {"s": True, "b": True, "mode": mode}

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

        # Match against triggers (Check 3-char first, then 2-char)
        matched_cfg = None
        trigger_len = 0

        if len(command_token) >= 3:
            prefix_3 = command_token[:3]
            if prefix_3 in trigger_map:
                matched_cfg = trigger_map[prefix_3]
                trigger_len = 3

        if not matched_cfg and len(command_token) >= 2:
            prefix_2 = command_token[:2]
            if prefix_2 in trigger_map:
                matched_cfg = trigger_map[prefix_2]
                trigger_len = 2

        if not matched_cfg:
            return None

        # 4. Extract Modifier (Strict Syntax)
        raw_mod = command_token[trigger_len:]
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
        # FIX: Typo fixed (acknowledge) and simplified for 8B models
        silence = "SILENT MODE: Do not explain. Start with header."
        if lang_code:
            target_lang = lang_code.upper()
            return (
                f"{silence}\n"
                f"TARGET LANGUAGE: {target_lang}.\n"
                f"Translate content to {target_lang}. Use {target_lang} for the key takeaways too."
            )
        else:
            return (
                f"{silence}\n"
                f"DETECT input language.\n"
                f"Respond in the SAME language."
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
        # FIX: Obfuscated pattern to prevent UI rendering bugs with thinking tags
        think_pattern = r"<" + "think>.*?</" + "think>"

        # Calculate word count (Cleaning thinking blocks)
        clean_content = re.sub(think_pattern, "", content, flags=re.DOTALL).strip()

        input_words = len(clean_content.split())
        smart_threshold = self.user_valves.smart_nano_threshold

        # Logic Variables
        explicit_mode = parsed["target_mode"]  # nano, schematic, table, brief, or None

        # Fix OWUI v0.8.x
        is_recursive = "## 🎯 Executive Summary" in content

        user_wants_nano = explicit_mode == "nano" or is_recursive

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

    def _is_compact_model(self, model_input: Any) -> bool:
        """
        Detect if the model is 'compact' (< 12B parameters or 'mini' variant).
        Accepts either a Model ID (str) or a Model Object (dict) from metadata.
        """
        try:
            model_id = ""
            param_str = ""

            # 1. Resolve Input Source (Dict vs String)
            if isinstance(model_input, dict):
                # Direct metadata provided in body
                model_id = model_input.get("id", "") or model_input.get("name", "")
                # Path: ollama -> details -> parameter_size
                param_str = (
                    model_input.get("ollama", {})
                    .get("details", {})
                    .get("parameter_size", "")
                )
            else:
                # Fallback: String ID provided -> Lookup in App State
                model_id = str(model_input)
                if self.request and hasattr(self.request.app.state, "MODELS"):
                    meta = getattr(self.request.app.state, "MODELS", {}).get(
                        model_id, {}
                    )
                    param_str = (
                        meta.get("ollama", {})
                        .get("details", {})
                        .get("parameter_size", "")
                    )

            # 2. Strategy A: Metadata Check (Explicit Size)
            if param_str:
                match = re.search(r"(\d+(?:\.\d+)?)", param_str)
                if match:
                    size = float(match.group(1))
                    is_compact = size < 12.0
                    if is_compact and self.debug:
                        self.debug.log(
                            f"Compact Model Detected (Size): {model_id} ({size}B)"
                        )
                    return is_compact

            # 3. Strategy B: Name Heuristics (Cloud/API Fallback)
            id_lower = model_id.lower()

            # Semantic keywords
            compact_keywords = ["mini", "flash", "haiku", "nano", "small"]
            if any(k in id_lower for k in compact_keywords):
                if self.debug:
                    self.debug.log(f"Compact Model Detected (Keyword): {model_id}")
                return True

            # Regex for explicit size in name (e.g. 8b, 7b)
            size_match = re.search(r"(\d+(?:\.\d+)?)b(?:$|[^a-z0-9])", id_lower)
            if size_match:
                size = float(size_match.group(1))
                if size < 12.0:
                    if self.debug:
                        self.debug.log(
                            f"Compact Model Detected (Regex): {model_id} ({size}B)"
                        )
                    return True

            return False

        except Exception as e:
            if self.debug:
                self.debug.log(f"Model detection error: {e}")
            return False

    def _get_prompt_template(
        self, mode: str, target_len: Optional[int], lang_instr: str, model_info: Any
    ) -> str:
        """Select and format the correct prompt template based on mode and model capability."""
        # ⚠️ DEBUG OVERRIDE: Bypass all logic if enabled
        if DEBUG_PROMPT_OVERRIDE:
            if self.debug:
                self.debug.log("⚠️ DEBUG PROMPT OVERRIDE ACTIVE")
            return DEBUG_PROMPT_TEMPLATE

        # Check for compact model
        is_compact = self._is_compact_model(model_info)

        # Determine config key
        cfg_key = mode
        if mode == "brief" and is_compact:
            cfg_key = "simple_brief"
            if self.debug:
                mid = (
                    model_info.get("id", "?")
                    if isinstance(model_info, dict)
                    else str(model_info)
                )
                self.debug.log(f"Using SIMPLE_BRIEF config for {mid}")

        # Load Configuration
        config = PROMPT_CONFIG.get(cfg_key, PROMPT_CONFIG["brief"])

        # --- DYNAMIC VISUAL ASSEMBLY ---
        allowed_keys = config.get("visuals", [])

        # 1. Build Lists & Strings
        allowed_names = []
        guidelines_parts = []
        syntax_parts = []
        # Note: Example header is still separate as it's part of the main template structure, not the visual rules
        example_block = config.get("example_header", "")

        for key in allowed_keys:
            asset = VISUAL_ASSETS.get(key)
            if asset:
                allowed_names.append(key)
                guidelines_parts.append(asset["rule"])
                syntax_parts.append(asset["syntax"])

        # 2. Format Components
        allowed_str = ", ".join(allowed_names) if allowed_names else "NONE"
        guidelines_str = (
            "\n".join(guidelines_parts) if guidelines_parts else "NO VISUALS ALLOWED."
        )
        syntax_str = "\n".join(syntax_parts)

        # --- END DYNAMIC ASSEMBLY ---

        # Determine Summary Block & Lengths
        if mode == "nano":
            summary_block = ""
            length_val = (
                f"{target_len}"
                if target_len
                else str(self.user_valves.max_nano_brief_length)
            )
        else:
            summary_block = SUMMARY_BLOCK_TEMPLATE.format(
                LENGTH=self.user_valves.summary_length
            )
            length_val = ""

        # Build Prompt
        prompt = MASTER_PROMPT.format(
            ACTION_TYPE=config["action"],
            SUMMARY_BLOCK=summary_block,
            STRUCTURE_BLOCK=config["structure"].replace("{LENGTH}", length_val),
            REPEAT_RULE=config.get("repeat_rule", DEFAULT_REPEAT_RULE),
            ALLOWED_VISUALS_LIST=allowed_str,
            VISUAL_GUIDELINES=guidelines_str,
            VISUAL_SYNTAX=syntax_str,
            EXAMPLE_BLOCK=example_block,
            LANGUAGE_INSTRUCTION=lang_instr,
        )

        # Inject dynamic lengths for Standard/Simple Brief
        if cfg_key in ["brief", "simple_brief"]:
            prompt = prompt.replace(
                "{{SYNTESYS_LENGTH}}", self.user_valves.synthesis_length
            )
            prompt = prompt.replace(
                "{{ANALYSYS_LENGTH}}", self.user_valves.analysis_length
            )

        if TRACE:
            self.debug.log(f"Prompt generated for mode {cfg_key}: {prompt}")

        return prompt

    def _construct_final_message(
        self, prompt: str, content: str, is_search: bool, lang_code: Optional[str]
    ) -> Tuple[str, str]:
        """
        Split the prompt into System Instructions and User Data.
        Returns: (system_prompt, user_content)
        """
        # FIX: Clean Query for Web Search to prevent RAG confusion
        if is_search:
            # For Search: System gets the rules, User gets the CLEAN query.
            # We rely on OWUI RAG to inject the context.
            system_prompt = (
                f"{prompt}\n\n"
                f"SYSTEM OVERRIDE: The user has requested a Web Search. "
                f"Use the Search Results (Context) provided by the system as your Source Data. "
                f"Ignore the standard chat style; output ONLY the Report requested in the System Prompt."
            )
            user_content = content  # Keep it clean for the search engine

        else:
            # For Text Analysis: We wrap the content explicitly
            fallback_instr = (
                "If ambiguous or mixed, default to ENGLISH." if not lang_code else ""
            )

            system_prompt = (
                f"{prompt}\n\n"
                f"SYSTEM OVERRIDE: DO NOT CHAT. DO NOT EXPLAIN. OUTPUT ONLY THE REPORT."
            )

            user_content = (
                f"*** BEGIN SOURCE DATA ***\n"
                f"{content}\n"
                f"*** END SOURCE DATA ***\n\n"
                f"{fallback_instr}"
            )

        return system_prompt, user_content

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

        # FIX: Robust Multimodal Text Extraction (v0.4.11)
        # Iterates through all parts of the message to find text, avoiding list-attribute errors
        last_msg = msg_list[-1].get("content", "")

        if isinstance(last_msg, list):
            # Join all text parts found in the list (skips images)
            txt = "\n".join(
                [
                    str(part.get("text", ""))
                    for part in last_msg
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
            )
        else:
            # Handle standard string content
            txt = str(last_msg)

        txt = txt.strip()

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

        if TRACE:
            self.debug.dump(body, "Body")

        await self.em.emit_status("EasyBrief Started", False)

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

            self.debug.log(f"Empty trigger detected. Using context: {content[:50]}...")

            if parsed["is_search"]:
                await self.em.emit_status("Extracting Search Query", False)
                content = await self._extract_query(
                    content, body.get("model"), __user__["id"], parsed["lang"]
                )
                self.debug.log(f"Extracted Query: {content}")
                await self.em.emit_status(f"Searching: {content[:60]}...", False)

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
            await self.em.emit_status("Input too short for Brief", True)
            if body["messages"]:
                body["messages"][-1]["content"] = content
            return body

        self.ctx.model.user_query, self.ctx.model.id = content, body.get("model")

        try:
            # Phase 5.5: Pre-Search Injection (Architecture A)
            if parsed["is_search"]:
                # Initialize Portable Handler
                search_handler = WebSearchHandler(
                    self.request, __user__["id"], self.em, self.debug
                )

                # Execute Search Cycle (Generate -> Search -> Process)
                search_context = await search_handler.search(
                    content, body.get("model"), self.user_valves.max_search_queries
                )

                if search_context:
                    # Update Content & Disable Features for Main Request
                    content = search_context

                    if "features" not in body:
                        body["features"] = {}
                    body["features"]["web_search"] = False
                    body["features"]["memory"] = False

                    # Treat as Local Brief now
                    parsed["is_search"] = False

            # --- DEBUG PROBE ---
            if TRACE:
                self.debug.log(f"PROBE: parsed['is_search'] = {parsed['is_search']}")
                self.debug.log(
                    f"PROBE: features.web_search = {body.get('features', {}).get('web_search')}"
                )
                self.debug.log(f"PROBE: content length = {len(content)}")
                self.debug.dump(content[:500], "PROBE: Content Preview")

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

                # Brief Generation Logic
                mode, target_len, status_msg = self._resolve_brief_mode(content, parsed)
                await self.em.emit_status(status_msg, False)

                model_input = body.get("metadata", {}).get("model") or body.get("model")
                selected_prompt = self._get_prompt_template(
                    mode, target_len, lang_instruction, model_input
                )

                # FIX: Split System and User messages for Llama 3 stability
                sys_prompt, user_data = self._construct_final_message(
                    selected_prompt, content, parsed["is_search"], parsed["lang"]
                )

                # Apply Model Parameters (Bias-Free Config)
                body["temperature"] = self.user_valves.temperature
                body["top_p"] = self.user_valves.top_p
                body["top_k"] = 30
                body["repeat_penalty"] = 1.0
                body["frequency_penalty"] = 0.0

                # NUCLEAR OPTION: Force strict [System, User] structure
                body["messages"] = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_data},
                ]
                self.debug.log("History wiped & Structure enforced: [System, User]")
                self.debug.log(
                    f"Model options: temperature:{body['temperature']}|top_p:{body['top_p']}|repeat_penalty:1|frequency_penalty:0"
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
                # Search mode keeps single user message for now (less critical)
                body["messages"] = [{"role": "user", "content": instr}]

            # Phase 7: Apply Features
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

        return body

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None  # type: ignore
    ) -> dict:
        """Process the outgoing response and restore web search state."""
        try:
            if self.ctx and self.ctx.model.executed:
                # Restore original model if it was swapped
                if self.ctx.model.original_model:
                    body["model"] = self.ctx.model.original_model

                if "features" in body:
                    body["features"]["web_search"] = self.ctx.model.web_search_original

                # Handle Output & Debug
                if "messages" in body and len(body["messages"]) > 0:
                    last_msg = body["messages"][-1]
                    content = last_msg.get("content", "")
                    debug_out = self.debug.emit()

                    if isinstance(content, str):
                        last_msg["content"] += debug_out
                    elif isinstance(content, list) and debug_out:
                        content.append({"type": "text", "text": debug_out})
                        last_msg["content"] = content

                self.debug.log("--- OUTLET COMPLETE ---")  # type: ignore

                # Minimal completion status
                await self.em.emit_status("EasyBrief completed", True)

        except Exception as e:
            # Safety net for outlet errors
            print(f"EasyBrief Outlet Error: {e}")

        finally:
            # ⚠️ CRITICAL FIX: Prevent State Leaking
            # Reset context to ensure subsequent requests (like Title Generation)
            # do not trigger this logic again using stale data.
            self.ctx = None

        return body

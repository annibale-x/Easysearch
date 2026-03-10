* 2026-03-10: v0.5.15 - Code Compliance & Documentation Overhaul (Hannibal)  
  * Compliance: Applied "Airy Code Style" formatting with mandatory blank lines before classes, after docstrings, and before control flow blocks (if/try/except).
  * Documentation: Enhanced method docstrings with parameter descriptions and return values across all core classes (ConfigService, ShadowRequest, WebSearchHandler, DebugService, etc.).
  * Sanitizer: Incremented MermaidSanitizer version to 2.0.14 reflecting compliance updates.
  * Imports: Added missing `random` import for User‑Agent rotation in web fetching.
  * Code Quality: Removed trailing whitespace, standardized internal spacing, and preserved all existing debug statements per project rules.

* 2026-03-07: v0.5.14 - Sanitizer Architecture Overhaul & Visual Hardening (Hannibal)  
  * Architecture: Split sanitization logic into `MermaidSanitizer` (portable) and `TemplateSanitizer` (EB-specific). Implemented unified Rolling Buffer in `stream` for robust real-time corrections.
  * Key Takeaways: Enforced H3 header (`###`), correct emoji (`📌`), and separator (`---`). Added negative constraints to prevent duplication inside topic loops.
  * Visuals: Hardened Pie Chart rules to prevent hallucinated data. Fixed "Fake Mermaid Tables" and stripped HTML `<table>` tags from Markdown tables.
  * Prompt: Added explicit `<WORKFLOW>` section to `MASTER_PROMPT`. Restricted compact models (<12B) to tables only.
  * Bug Fixes: Resolved stream truncation issues and `DebugService` attribute errors.

* 2026-03-07: v0.5.13 - Legacy Sanitizer Removal & Debug Fix (Hannibal)  
  * Removed redundant legacy `_sanitize_output` and `_sanitize_text_markers` methods since sanitization is now fully handled in-stream.
  * Fixed `AttributeError` in `DebugService` caused by referencing a non-existent `output` attribute.

* 2026-03-07: v0.5.12 - Stream Status Completion Fix (Hannibal)  
  * Fixed an issue where the frontend status indicator would hang indefinitely on "Generating..." by passing the correct `__event_emitter__` object to the `outlet` method.

* 2026-03-07: v0.5.11 - Robust Markdown Spacing & Implicit Closure Fix (Hannibal)  
  * Refactored regex for horizontal separators (`---`) to properly isolate them with `\n\n` without breaking Markdown tables.
  * Fixed implicit Mermaid block closure to correctly append `\n```\n\n` while handling preceding line breaks properly.
  * Resolved formatting issues causing text to stick to headers after hallucinated code blocks.

* 2026-03-07: v0.5.10 - Advanced Markdown & Mermaid Hallucination Fixes (Hannibal)  
  * Added implicit Mermaid block closure to prevent unclosed code blocks from bleeding into markdown structure.
  * Expanded hallucination patch to intercept and correct `[mermaid]` tags.
  * Enforced proper spacing for horizontal rules (`---`) by injecting empty lines.

* 2026-03-07: v0.5.9 - MITM Stream Session Activation Fix (Hannibal)  
  * Fixed a bug where the MITM stream session was bypassed because it was never initialized with `bypass: False` during the `inlet` phase.
  * Ensures the MITM streaming pipeline is properly activated when EasyBrief is triggered.

* 2026-03-07: v0.5.8 - Generalized Mermaid Hallucination Patch (Hannibal)  
  * Generalized the MITM hallucination patch to dynamically support all Mermaid diagram types (gantt, erDiagram, sequenceDiagram, etc.) beyond just pie, graph, and mindmap.

* 2026-03-07: v0.5.7 - MITM Hallucination Patch & Stream Flush (Hannibal)  
  * Implemented MITM patch to convert hallucinated tags (`[pie]`, `[graph TD]`, `[mindmap]`) into valid Mermaid blocks.
  * Added filter to silently strip erroneous `[table]` text markers from stream.
  * Enhanced stream buffer logic to handle `finish_reason` and properly flush/close Mermaid blocks at the end of generation.

* 2026-03-07: v0.5.6 - Code Cleanup (Hannibal)  
  * Removed unused `UserModel` from imports.
  * Removed unused `Union` typing from imports.

* 2026-03-07: v0.5.5 - MITM Logic Integration & SoC Refactoring (Hannibal)  
  * Implemented full Man-in-the-Middle (MITM) streaming architecture.
  * Refactored Mermaid sanitizers into a dedicated `MermaidSanitizer` class (SoC).
  * Reordered Open WebUI hooks (`inlet`, `stream`, `outlet`) for readability.
  * Cleaned up obsolete comments and added comprehensive documentation.

* 2026-03-07: v0.5.4 - MITM Logic Pre-integration (Hannibal)  
  * Implemented preliminary framework for Man-in-the-Middle streaming architecture.
  * Integrated Mermaid sanitizer components from mermaid-doctor repository.
  * Prepared foundation for real-time Mermaid diagram correction.
  * Added modular sanitizer service architecture for future extensibility.
  * Initial integration of buffering and session management logic.

* 2026-03-01: v0.5.3 - Prompt Optimization & Sanitizer Pipeline (Hannibal)  
  * Reverted architecture to standard System Prompt injection.
  * Optimized mindmap prompt from negative constraints to active task ("Remove parentheses from labels text").
  * Implemented robust multi-stage output sanitization pipeline (`_sanitize_output`).
  * Added Depth-Parser logic in `_sanitize_mermaid_mindmap` to handle nested bracket edge cases gracefully.
  * Added `_sanitize_mermaid_graph` to fix trailing character syntax errors in graph TD.
  * Added `_sanitize_text_markers` to remove conversational LLM noise.
  * Configured sanitizers to be globally toggled via `SANITIZE_OUTPUT` boolean constant.

* 2026-03-01: v0.5.2 - Web Search Engine Upgrade & Turbo Loader Integration (Hannibal)
  * Ported advanced WebSearchHandler from EasySearch with lxml parsing and fallback snippets.
  * Implemented ShadowRequest v2 proxy with dictionary-based dynamic overrides.
  * Added concurrent HTTPX fetching with User-Agent rotation and strict timeout/size limits.
  * Integrated oversampling factor and auto-recovery fetch (Gap-Filler) for resilient web scraping.
  * Unified configuration state in ConfigService (Admin vs User valves priority).

* 2026-02-26: v0.5.1 - Turbo Architecture & Stability (Hannibal)
  * Major Refactor: Introduced `ShadowRequest` and `httpx` parallel loader.
  * UI Overhaul: Native search pills and professional status messages.
  * Bugfix: Solved double-execution issue on chat title generation (State Cleanup).

* 2026-02-26: v0.4.29 - Turbo Web Loader & Shadow Request (Hannibal)
  * Implemented `ShadowRequest` proxy to safely bypass OWUI's default loader without race conditions.
  * Added `_fetch_concurrently` using `httpx` for parallel, high-speed HTML retrieval.
  * Integrated `lxml` for surgical DOM cleaning (removing navs, footers, scripts).
  * Enhanced heuristic cleaning pipeline (regex) for fallback text.
  * Added support for Proxy and Custom CA Bundles in `httpx` client.

* 2026-02-25: v0.4.28 - Web Search Architecture Overhaul (Hannibal)
  * WebSearchHandler: Introduced a portable, self-contained class to manage query generation, execution, and result processing.
  * Query Expansion: Added logic to generate multiple search queries (up to 10) from a single user prompt for broader coverage.
  * Citation Recovery: Implemented manual extraction and emission of citations to replicate the native UI badge experience.
  * Context Cleaning: Added a regex-based cleaning pipeline to sanitize web search results (whitespace normalization, noise removal) before LLM injection.
  * Safety Mechanisms: Enforced hard disable of native `web_search` and `memory` features during brief generation to prevent hallucinations and double processing.
  * Error Handling: Improved error reporting for search failures and user object validation.

* 2026-02-25: v0.4.23 - Pre-Search Injection Architecture (Hannibal)
  * Implemented background search in inlet to bypass RAG context pollution.
  * Added citation recovery and re-emission for background searches.
  * Forced memory disable during brief generation to prevent context bleeding.

* 2026-02-25: v0.4.22 - Visual Discretion & Syntax Hardening (Hannibal)
  * Implemented "Explicit Skip Protocol" for all visual assets (Table, Mindmap, Graph, Pie) to prevent forced visualizations.
  * Hardened Mermaid Pie syntax: added mandatory "Market Share" check and strict prohibition of percentage symbols.
  * Refined Mermaid Mindmap rules: rewritten indentation logic to enforce strict 2-space hierarchy.
  * Refined Mermaid Graph rules: improved connector syntax definition to reduce syntax errors.
  * Enforced Emoji usage: added strict instruction for the 📌 emoji in Key Takeaways.

* 2026-02-25: v0.4.21 - Removed `_suppress_output()` dead logic (Hannibal)

* 2026-02-24: v0.4.19 - Llama 3 Stability & Pie Chart Fixes (Hannibal)
  * Implemented strict `[System, User]` role separation in `inlet` to prevent Llama 3 from hallucinating instructions into content.
  * Added explicit `PIE_EXAMPLE` constant and injection logic to fix Mermaid syntax errors (e.g., `title("...")`).
  * Enforced `CRITICAL: NO percentage symbol %` rule in `MASTER_PROMPT` to stop Llama 3 from breaking Pie Charts.
  * Refined `SUMMARY_BLOCK_TEMPLATE` with "dense summary" and "maximum information density" directives to stabilize output length variance.
  * Locked the `## 🎯 Executive Summary` header with an explicit `(Use EXACTLY this header...)` constraint to prevent emoji drift.

* 2026-02-24: v0.4.18 - Model Parameters & Visual Logic Fixes (Hannibal)
  * Added `temperature` (default 0.15) and `top_p` (default 0.8) to User Valves for fine-grained control over model creativity.
  * Hardcoded `repeat_penalty=1.0` and `frequency_penalty=0.0` to prevent syntax errors in Mermaid/Markdown generation.
  * Removed obsolete `FORCE_SIMPLE_BRIEF` logic; model capability detection is now fully dynamic.
  * Refined `VISUAL_GUIDELINES` to strictly forbid Pie Charts unless explicit percentage data is present in the source text (anti-hallucination fix).

* 2026-02-23: v0.4.17 - KISS Refactor & Dynamic Visual Logic (Hannibal)
  * The `key takeaways` have been tamed.
  * Refactored `MASTER_PROMPT` and constants to a "Keep It Simple" architecture optimized for small models (<12B).
  * Implemented dynamic injection of `VISUAL_GUIDELINES` based on model capabilities (Standard vs Compact).
  * Added dynamic assembly of One-Shot examples in `_get_prompt_template` to strictly match allowed visuals.
  * Fixed critical typo in language instructions (`akcnoledge` -> `acknowledge`) and simplified directive.
  * Enforced strict Mermaid syntax rules (mandatory quotes `("Node")` and strict indentation) to prevent rendering errors.
  * Removed contradictory visual rules (e.g., Graph allowed/forbidden conflicts) via logic separation.

* 2026-02-23: v0.4.16 - Prompt Refactoring & Pie Chart Fixes (Hannibal)  
  * Refactored `PROMPT_CONFIG` to use inheritance from `DEFAULT_BRIEF_CONFIG`, reducing duplication.
  * Added explicit `Pie Charts` rule to `MASTER_PROMPT` to fix syntax errors (`mermaid pie` vs `pie`).
  * Removed `summary_len` from config, now relying solely on `UserValves.summary_length`.
  * Removed Pie Chart examples from `brief` and `simple_brief` to prevent hallucination (Recency Bias).
  * Added "Soft Nudge" instruction ("Use `pie` for market share...") to encourage spontaneous usage when data exists.

* 2026-02-23: v0.4.15 - Modular Prompt Architecture & Compact Model Support (Hannibal)  
  * Introduced `MASTER_PROMPT` and `PROMPT_CONFIG` for centralized and modular prompt management.
  * Implemented `simple_brief` mode specifically optimized for compact models (<12B) with simplified visual rules (no Graph TD/LR).
  * Added robust compact model detection (`_is_compact_model`) using both metadata inspection and name heuristics.
  * Unified report structure across standard and simple briefs to ensure consistency while adapting visual complexity.
  * Added `FORCE_SIMPLE_BRIEF` constant to facilitate testing of the simplified prompt logic on all models.

* 2026-02-22: v0.4.14 - Add SIMPLE_BRIEF_PROMPT for stupid models (<12b) (Hannibal)

* 2026-02-22: v0.4.13 - Obfuscated pattern to prevent UI rendering bugs with thinking tags (Hannibal)

* 2026-02-22: v0.4.12 - Silent Mode & Robust Persistence (Hannibal)
  * Fixed recursion detection logic in `_resolve_brief_mode`. Now relies on the visual signature (`## 🎯`) instead of the invisible watermark, solving persistence issues in Open WebUI DB.
  * Implemented "SILENT EXECUTION" protocol in prompts and language instructions to stop Llama 3 (8b) models from generating meta-talk.
  * Refactored all Prompt Templates (Nano, Table, Schematic, Brief) with `[SYSTEM: SILENT_MODE=ON]` header and "Raw Data" structure to prevent prompt leaking.
  
* 2026-02-22: v0.4.10 - Documentation Overhaul & Syntax Fixes (Hannibal)
  * Updated README.md with rigorous command syntax (b>, s>, t>, n>).
  * Clarified RAG/PDF limitations (Context-only processing vs Vector DB).
  * Detailed User Valves configuration with natural language examples.
  * Refined "Smart Nano" and "Watermark" logic explanations.

* **2026-02-21**: v0.4.9 - Semantic Trigger Symmetry (Hannibal)
  * Refactored `_parse_trigger` logic to support variable-length command tokens.
  * Introduced "Sandwich Syntax" for Web Search Briefs (e.g., `?n>`, `?s>`, `?t>`) to align with the logical brief operator `>`.
  * Harmonized the mental model: `?` (Source: Web) + `x` (Mode) + `>` (Action: Brief).

* **2026-02-21**: v0.4.8 - Filter.inlet Logic Modularization (Hannibal)  
  * Refactored the monolithic `Filter.inlet` method into dedicated helper functions (`_resolve_brief_mode`, `_get_prompt_template`).
  * Decoupled "Smart Nano" threshold logic and model swapping from the main execution flow.
  * Improved code maintainability and readability by reducing cyclomatic complexity.
  * No functional changes to the end-user experience.

* **2026-02-21**: v0.4.7 - Prompt Modularization & Architecture Refactor (Hannibal)

* **2026-02-21**: v0.4.6 - enforce Overview->Context->Visual flow in SCHEMATIC_PROMPT (Hannibal)

* **2026-02-21**: v0.4.5 - Rich Brief renamed in brief (trigger R->B) (Hannibal)   

* **2026-02-21**: v0.4.4 - complete refactor of BRIEF_PROMPT (Hannibal)   

* **2026-02-20**: v0.4.3 - fixes and minor optimizations (Hannibal)   

* **2026-02-20**: v0.4.2 - new syntax, nano, table, schematic and rich brief, prompt tuning (Hannibal)   

* **2026-02-20**: v0.3.7 - nano, simple and rich brief (Hannibal)   

* **2026-02-19**: v0.2.4 - general fixes and query extraction from assistant message (Hannibal)   

* **2026-02-19**: v0.2.1 - costants moved to user valves, add task model management (Hannibal)   

* **2026-02-19**: v0.1.7 - prompt tuning for small models (Hannibal)   

* **2026-02-19**: v0.1.6 - add valves search, brief and search and brief triggers (Hannibal)   

* **2026-02-19**: remove junk files (Hannibal)                                                                                                                        
* **2026-02-19**: gitignore (Hannibal)                                                                                                                                
* **2026-02-18**: v0.1.5 - Prompt refinement and filter context reset (Hannibal)                                                                                      
* **2026-02-18**: v0.1.2 - add meta-lengths to the brief prompt (Hannibal)                                                                                            
* **2026-02-18**: v0.1.1 - Fix mermaid and TD rules in prompt (Hannibal)                                                                                              
* **2026-02-18**: v0.1.0 - Prompt refinement (Hannibal)                                                                                                               
* **2026-02-18**: v0.0.9 - add dump search "?" trigger (Hannibal)                                                                                                     
* **2026-02-18**: v0.0.8 - Prompt refinement, works quite well with tables, pies, mindmaps (Hannibal)                                                                 
* **2026-02-18**: v0.0.7 - Prompt tuning (Hannibal)                                                                                                                   
* **2026-02-17**: v0.0.3 - Minimal prompt, structured web results are ok (Hannibal)                                                                                   
* **2026-02-17**: Rename EasySearch -> EasyBrief (Hannibal)                                                                                                           
* **2026-02-17**: Merge branch 'main' into dev (Hannibal)                                                                                                             
* **2026-02-17**: add README.md (Hannibal)                                                                                                                            
* **2026-02-17**: v0.0.2 - Full reset (Hannibal)                                                                                                                      
* **2026-02-16**: Add Easysearch section to README (Hannibal)                                                                                                         
* **2026-02-16**: Initial commit (Hannibal)

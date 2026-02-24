* 2024-05-24: v0.4.19 - Llama 3 Stability & Pie Chart Fixes (Hannibal)
  * Implemented strict `[System, User]` role separation in `inlet` to prevent Llama 3 from hallucinating instructions into content.
  * Added explicit `PIE_EXAMPLE` constant and injection logic to fix Mermaid syntax errors (e.g., `title("...")`).
  * Enforced `CRITICAL: NO percentage symbol %` rule in `MASTER_PROMPT` to stop Llama 3 from breaking Pie Charts.
  * Refined `SUMMARY_BLOCK_TEMPLATE` with "dense summary" and "maximum information density" directives to stabilize output length variance.
  * Locked the `## 🎯 Executive Summary` header with an explicit `(Use EXACTLY this header...)` constraint to prevent emoji drift.

* 2024-05-24: v0.4.18 - Model Parameters & Visual Logic Fixes (Hannibal)
  * Added `temperature` (default 0.15) and `top_p` (default 0.8) to User Valves for fine-grained control over model creativity.
  * Hardcoded `repeat_penalty=1.0` and `frequency_penalty=0.0` to prevent syntax errors in Mermaid/Markdown generation.
  * Removed obsolete `FORCE_SIMPLE_BRIEF` logic; model capability detection is now fully dynamic.
  * Refined `VISUAL_GUIDELINES` to strictly forbid Pie Charts unless explicit percentage data is present in the source text (anti-hallucination fix).

* 2024-05-23: v0.4.17 - KISS Refactor & Dynamic Visual Logic (Hannibal)
  * The `key takeaways` have been tamed.
  * Refactored `MASTER_PROMPT` and constants to a "Keep It Simple" architecture optimized for small models (<12B).
  * Implemented dynamic injection of `VISUAL_GUIDELINES` based on model capabilities (Standard vs Compact).
  * Added dynamic assembly of One-Shot examples in `_get_prompt_template` to strictly match allowed visuals.
  * Fixed critical typo in language instructions (`akcnoledge` -> `acknowledge`) and simplified directive.
  * Enforced strict Mermaid syntax rules (mandatory quotes `("Node")` and strict indentation) to prevent rendering errors.
  * Removed contradictory visual rules (e.g., Graph allowed/forbidden conflicts) via logic separation.

* 2025-02-23: v0.4.16 - Prompt Refactoring & Pie Chart Fixes (Hannibal)  
  * Refactored `PROMPT_CONFIG` to use inheritance from `DEFAULT_BRIEF_CONFIG`, reducing duplication.
  * Added explicit `Pie Charts` rule to `MASTER_PROMPT` to fix syntax errors (`mermaid pie` vs `pie`).
  * Removed `summary_len` from config, now relying solely on `UserValves.summary_length`.
  * Removed Pie Chart examples from `brief` and `simple_brief` to prevent hallucination (Recency Bias).
  * Added "Soft Nudge" instruction ("Use `pie` for market share...") to encourage spontaneous usage when data exists.

* 2025-02-23: v0.4.15 - Modular Prompt Architecture & Compact Model Support (Hannibal)  
  * Introduced `MASTER_PROMPT` and `PROMPT_CONFIG` for centralized and modular prompt management.
  * Implemented `simple_brief` mode specifically optimized for compact models (<12B) with simplified visual rules (no Graph TD/LR).
  * Added robust compact model detection (`_is_compact_model`) using both metadata inspection and name heuristics.
  * Unified report structure across standard and simple briefs to ensure consistency while adapting visual complexity.
  * Added `FORCE_SIMPLE_BRIEF` constant to facilitate testing of the simplified prompt logic on all models.

* 2024-02-22: v0.4.14 - Add SIMPLE_BRIEF_PROMPT for stupid models (<12b) (Hannibal)

* 2024-02-22: v0.4.13 - Obfuscated pattern to prevent UI rendering bugs with thinking tags (Hannibal)

* 2024-02-22: v0.4.12 - Silent Mode & Robust Persistence (Hannibal)
  * Fixed recursion detection logic in `_resolve_brief_mode`. Now relies on the visual signature (`## 🎯`) instead of the invisible watermark, solving persistence issues in Open WebUI DB.
  * Implemented "SILENT EXECUTION" protocol in prompts and language instructions to stop Llama 3 (8b) models from generating meta-talk.
  * Refactored all Prompt Templates (Nano, Table, Schematic, Brief) with `[SYSTEM: SILENT_MODE=ON]` header and "Raw Data" structure to prevent prompt leaking.
  
* 2024-02-22: v0.4.10 - Documentation Overhaul & Syntax Fixes (Hannibal)
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
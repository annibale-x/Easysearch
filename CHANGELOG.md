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
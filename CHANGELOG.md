* **2026-02-20**: v0.4.4 - Document Intelligence & Attachment Support (Hannibal)  
  
  * **Document Support**: Added native detection and processing for file attachments (PDF, DOCX, CSV) and images.
  
  * **Context Preservation**: The Isolation Mode now intelligently preserves `files` and `images` keys while wiping chat history, enabling RAG/Vision context injection.
  
  * **Smart Nano Override**: Logic updated to disable "Auto-Nano" when attachments are present, preventing large documents from being compressed due to short trigger commands.
  
  * **Dynamic Prompting**: Prompt header now adapts to `=== ATTACHED CONTEXT ANALYSIS ===` when files are detected.
  
  * **Capability Engine**: Added `_get_capabilities` method to inspect global model registry for vision and file context support.

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
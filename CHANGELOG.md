### Riepilogo dello stato finale (v0.0.9):

1.  **Trigger Multipli & Parsing**:
    *   `??[:lang]` -> Ricerca Web + Briefing Evoluto (Mermaid + Tabelle).
    *   `!![:lang]` -> Solo Briefing Evoluto su testo fornito o contesto.
    *   `?[:lang]` -> Ricerca Web standard (senza briefing forzato).
2.  **Logica Prompt Adattiva**:
    *   `rich_output` (User Valve): Se `True`, usa il `BRIEF_PROMPT` (Mermaid, Mindmap consolidati, Tabelle). Se `False`, usa il `SIMPLE_PROMPT` (Solo tabelle e testo).
    *   **Mindmap**: Vincolato a un unico blocco ad alta densità all'inizio del report per evitare frammentazioni.
    *   **Sintassi Mermaid**: Protezione totale contro i caratteri speciali `() [] {}` (sostituiti da trattini) e obbligo di virgolette per le etichette.
    *   **Tabelle**: Rigorosamente "naked" (senza backticks) per garantire il rendering fluido in Open WebUI.
3.  **Architettura Servizi**:
    *   Logica di parsing isolata in `_parse_trigger` per una manutenzione più semplice.
    *   `outlet` con cattura della `raw_assistant_response` per scopi di debug e analisi.
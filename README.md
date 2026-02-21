# 🎯 EasyBrief: Executive Reporting & Visual Intelligence
**Transform chaotic text, massive logs, and web searches into structured, high-density Executive Reports.**

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)](https://github.com/annibale-x/open-webui-easybrief)
![Open WebUI Filter](https://img.shields.io/badge/Open%20WebUI-Filter-blue?style=flat&logo=openai)

---

## 💡 Core Concept

**EasyBrief is a structural enforcement layer for Open WebUI.**

Its purpose is to allow a decision-maker to grasp the core meaning, logic, and data of a complex topic in **under 3 minutes**.

Unlike standard summarizers that simply truncate text, EasyBrief reorganizes information into a standardized **Executive Report** format (approx. 800-1600 words). It forces the LLM to abandon conversational fillers and prioritize:
*   **Hierarchical Structure**: Executive Overviews, Concept Synthesis, and Analytical Insights.
*   **Visual Data**: Markdown Tables for data and Mermaid Diagrams for logic/flows.
*   **High Compression**: It is designed to ingest large amounts of text. **Note:** If you feed it 100,000 words, it will still output a max of ~2,000 words. This implies a **50:1 compression ratio**, meaning fine details will be sacrificed in favor of macro-trends and critical logic.

### Key Capabilities
1.  **Context Agnostic**: Works on text you paste, the **previous message** in chat, or web search results.
2.  **Isolation Mode**: Temporarily ignores previous chat history during generation to ensure the report is strictly based on the provided input (zero hallucinations).
3.  **Recursive Logic**: Can compress its own outputs (e.g., turning a Standard Brief into a Nano Brief).

---

## ⚠️ Important Note on Documents (RAG)

**EasyBrief operates on the active context window.**
It does **not** automatically scan files inside Open WebUI's Vector Database (RAG).
*   **Supported**: Text you paste directly, or text explicitly retrieved by the LLM into the chat window.
*   **Not Supported (Yet)**: Uploading a PDF and expecting EasyBrief to read it without the LLM first retrieving the content.

> *🚀 **Roadmap**: A strictly experimental branch is currently in development to support native document parsing (PDF/Images) directly within the filter pipeline.*

---

## 📊 The 4 Briefing Modes

| Mode | Trigger Code | Target | Description |
| :--- | :--- | :--- | :--- |
| **STANDARD** | `b` | **Executives** | **The Full Report.** Balanced depth. Includes Overview, Synthesis, Analysis, and Visuals. Target length: 800-1600 words. |
| **SCHEMATIC**| `s` | **Engineers** | **Visual Logic.** Prioritizes Mermaid diagrams (Flowcharts, Mindmaps) and structured tables. Minimal narrative text. |
| **TABLE** | `t` | **Analysts** | **Pure Data.** Converts lists, comparisons, and specs into clean Markdown grids. Ideal for Excel/CSV export. |
| **NANO** | `n` | **Triage** | **The "Elevator Pitch".** A single paragraph + 5 key takeaways (max 150 words). Use for quick mobile reading. |

> **Shortcut**: The command `>>` triggers your **Default Mode** (configurable in Settings).

---

## 🎮 Command Reference

Syntax: `[WebPrefix][Mode][BriefSuffix]` -> e.g., `?t>`
*   **Suffix**: Always ends with `>` to trigger a Brief.
*   **Prefix**: Start with `?` to enable Web Search.

### 1. Local Context (Analyze Text)
Use these commands to process **text you paste** OR to summarize the **last message** received from the LLM.

| Command | Function |
| :--- | :--- |
| **`>>`** | **Smart Default**: Generates a report using your preferred settings. |
| **`n>`** | **Force Nano**: Compresses content into a flash summary. |
| **`s>`** | **Force Schematic**: Focuses on diagrams and flows. |
| **`t>`** | **Force Table**: Extracts data into grids. |
| **`b>`** | **Force Standard**: Generates the full executive report. |

### 2. Web Intelligence (Research & Report)
Use these to ask a question. The system will search the web and compile the results.

| Command | Function |
| :--- | :--- |
| **`?> <query>`** | **Search & Brief**: Research -> Default Report. |
| **`?n> <query>`** | **Search & Nano**: Research -> Quick Answer. |
| **`?s> <query>`** | **Search & Schematic**: Research -> Mindmaps/Flowcharts. |
| **`?t> <query>`** | **Search & Table**: Research -> Comparison Tables. |
| **`?b> <query>`** | **Search & Standard**: Research -> Full Report. |

### 3. Search Only (Passthrough)
| Command | Function |
| :--- | :--- |
| **`?? <query>`** | **Explicit Search**: Forces a web search on the query, but returns a normal chat answer (no Brief formatting). |
| **`??`** | **Auto-Context Search**: Reads the *previous* message in chat, generates a search query automatically, and answers using web results. |

### 4. Language Control
Append `:<lang_code>` to any command to force the output language.
*   `>>:it` (Analyze -> Output in **Italian**)
*   `?t>:es` (Search -> Output Tables in **Spanish**)

---

## ⚙️ Configuration (User Valves)

You can customize the behavior of EasyBrief via the **Valves** menu in Open WebUI.

### General Settings
*   **`default_brief_mode`**:
    *   *Options:* `brief`, `schematic`, `table`, `nano`.
    *   *Function:* Determines what happens when you type `>>` or `?>`.
*   **`task_model`**:
    *   *Function:* **Model Swapping**. Allows you to use a specific model (e.g., GPT-4o, Claude 3.5 Sonnet) for generating Briefs, even if your current chat is using a smaller model (e.g., Llama 3). Leave empty to use the current chat model.
*   **`debug`**:
    *   *Function:* Enables verbose logging to the console for troubleshooting.

### Smart Logic
*   **`smart_nano_threshold`** (Default: `300`):
    *   *Function:* If the input text is shorter than this word count, `>>` will automatically switch to **Nano Mode**.
    *   *Why:* Prevents generating a massive report for a short email. Set to `0` to disable.
*   **`max_nano_brief_length`** (Default: `200`):
    *   *Function:* The target word count for Nano Briefs.

### Prompt Engineering (Natural Language)
These settings control the verbosity of the **Standard Brief**. You can use **Natural Language** to define them.

*   **`overview_length`** (Default: `max 100 words`):
    *   *Examples:* `1-2 sentences`, `very concise`, `max 50 words`.
    *   *Function:* Controls the length of the "Executive Overview" section.
*   **`synthesis_length`** (Default: `max 80 words`):
    *   *Examples:* `detailed paragraph`, `bullet points`, `max 150 words`.
    *   *Function:* Controls the text block *before* the visual element.
*   **`analysis_length`** (Default: `max 40 words`):
    *   *Examples:* `1 sentence`, `deep analysis`, `max 100 words`.
    *   *Function:* Controls the "Analytical Insight" block that explains the diagram/table.

---

## 💼 Real-World Workflows

### 1. The "Wall of Text" Triage
**Scenario**: You receive a raw transcript of a 2-hour meeting (15,000 words).
**Action**: Paste the text and type `b>` (Standard Brief).
**Result**: EasyBrief compresses the 15k words into a ~1,200-word report. It separates "Chit-chat" from "Key Decisions", lists action items in a table, and provides an executive summary. **Time saved: ~45 minutes.**

### 2. Competitor Analysis (Web)
**Scenario**: You need to compare features of iPhone 16 vs Samsung S25.
**Action**: Type `?t> iPhone 16 vs Samsung S25 specs`.
**Result**: A **Table Brief**. The system searches the web and outputs a clean comparison matrix (Price, Features, Pros, Cons) ready for Excel.

### 3. The "Auto-Google" (Context Search)
**Scenario**: The LLM mentions "The 2024 EU AI Act" in a response, but you don't know what that is.
**Action**: Type `??`.
**Result**: EasyBrief reads the previous message, formulates a query like *"2024 EU AI Act summary requirements"*, searches Google, and explains it to you.

### 4. Recursive Compression
**Scenario**: You generated a Standard Brief (`b>`) but it's still too long for a quick email update.
**Action**: Type `n>` (Nano Brief) on the result.
**Result**: EasyBrief detects the previous output and compresses the 1,200-word report into a 150-word summary suitable for mobile messaging.

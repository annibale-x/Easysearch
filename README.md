
## 🎯 EasyBrief v0.4.3: Executive Summary & Search Assistant

Transform chaotic text and web searches into structured, professional Executive Reports with tables, mindmaps, and zero fluff.

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)](https://github.com/annibale-x/open-webui-easybrief)
![Open WebUI Filter](https://img.shields.io/badge/Open%20WebUI-Filter-blue?style=flat&logo=openai)
![License](https://img.shields.io/github/license/annibale-x/open-webui-easybrief?color=green)

![EasyBrief Demo](https://github.com/annibale-x/open-webui-easybrief/raw/main/assets/screencast.gif)
*(Above: Generating a Schematic Brief with one click)*

---

### 🚀 At a Glance: Why use EasyBrief?

Standard LLMs are chatty. They love to talk, use polite preambles, and bury data in walls of text. 
**EasyBrief** forces the model to act like a **Senior Business Analyst**: strictly structured, visual, and data-driven.

- **Stop Reading, Start Scanning**: Turn long emails, PDFs, or articles into dense **Executive Summaries** (`>>`).
- **Visual Intelligence**: Automatically convert text into **Flowcharts**, **Mindmaps**, and **Markdown Tables** (`s>`).
- **Web Research, Solved**: Don't just search Google. Research a topic and get a unified report with citations and data comparison tables (`?t`).
- **Mobile Friendly**: On the go? Generate a **Nano Brief** (`n>`) to get the core message in under 150 words.
- **Data First**: Force the model to output *only* tables for Excel/CSV export (`t>`).

---

### 📖 The Philosophy

**EasyBrief** was designed for professionals who need actionable intelligence, not conversation. 
It acts as a "strict filter" between you and the LLM, injecting rigorous templates that forbid "fluff", conversational fillers, and unstructured data.

It operates in **Isolation Mode**: every Brief is generated in a clean context, ensuring the model focuses *only* on the specific text or search query provided, without getting confused by previous chat history.

---

### 💡 The 4 Modes of Briefing

You can choose how you want your information delivered. Set your default in the **User Controls**, or trigger them on the fly.

| Mode | Trigger | Best For... | Output Style |
| :--- | :--- | :--- | :--- |
| **RICH** | `r>` | **Deep Analysis** | The full package: Executive Overview, Mindmaps, Detailed Synthesis, Analysis, and Key Takeaways. |
| **SCHEMATIC**| `s>` | **Logic & Flows** | **Visuals first**. Prioritizes Mermaid diagrams (Flowcharts, Mindmaps) and structured tables. No narrative text. |
| **TABLE** | `t>` | **Data & Specs** | **Strictly Tables**. Converts lists, comparisons, and specs into clean Markdown grids. Zero chat. |
| **NANO** | `n>` | **Mobile / Quick** | **Flash Brief**. A single paragraph + 5 bullet points. Max 150 words. Ideal for phone screens. |

> **Smart Nano**: If you ask for a standard brief (`>>`) on a very short text (e.g., a 5-line email), EasyBrief automatically switches to **Nano Mode** to avoid generating a report longer than the original text.

---

### 🎮 Usage & Command Schema

EasyBrief uses a simple **2-character syntax**. 
*   **`>` (Brief)**: Processes the text you typed (or the last message in chat).
*   **`?` (Search)**: Searches the Web and generates a report.

#### 1. Processing Text (Local Context)
Use these when you want to summarize/restructure text already in the chat or pasted in the input.

| Command | Action |
| :--- | :--- |
| **`>>`** | **Default Brief**: Uses your preferred mode (set in User Settings). |
| **`s>`** | **Schematic Brief**: Convert input into Diagrams and Logic Flows. |
| **`t>`** | **Table Brief**: Extract all data into Tables. |
| **`n>`** | **Nano Brief**: Compress input into a flash summary. |
| **`r>`** | **Rich Brief**: Force a full detailed report. |

#### 2. Web Research (Search & Report)
Use these to ask a question. The system will search Google/DuckDuckGo and compile the results.

| Command | Action |
| :--- | :--- |
| **`?? <query>`** | **Quick Search**: Just get the answer (Standard Web Search). |
| **`?> <query>`** | **Search & Brief**: Search the web -> Generate a **Default** Report. |
| **`?t <query>`** | **Search & Table**: Search -> Compile results into **Tables** (Great for product comparisons). |
| **`?s <query>`** | **Search & Schematic**: Search -> Visualize results with **Mindmaps**. |
| **`?n <query>`** | **Search & Nano**: Search -> Give me the quick answer (Flash Brief). |

#### 3. Language Modifiers
You can force the output language by appending it to the command.
*   **Format**: `[Command]:[Lang]` or just `[Command][Lang]`
*   **Examples**:
    *   `>>:it` (Analyze text -> Output in **Italian**)
    *   `?t:es` (Search Web -> Output Tables in **Spanish**)
    *   `n>fr` (Summarize -> Nano Brief in **French**)

---

### ⚡ Workflow Examples

**Scenario 1: Product Comparison**
You want to compare the iPhone 16 and Samsung S25 specs without reading 10 articles.
> **User**: `?t:en iPhone 16 vs Samsung S25 specs`
> **EasyBrief**: Searches the web, ignores the fluff, and outputs a single, clean **Markdown Table** comparing CPU, RAM, Camera, and Battery.

**Scenario 2: Understanding Complex Logic**
You paste a complex technical documentation about a Kubernetes architecture.
> **User**: `s>` (on the pasted text)
> **EasyBrief**: Generates a **Mermaid Flowchart** visualizing the architecture and a Mindmap of the components.

**Scenario 3: Mobile Summary**
You are on your phone and receive a long email chain.
> **User**: `>>` (Auto-switches to **Nano** if text is short)
> **EasyBrief**: "🎯 **Nano Brief**: The client is asking for a discount. **Key Concepts**: 1. Budget cut. 2. Deadline extended."

---

### 🔧 Configuration (Valves)

You can customize EasyBrief in the **Valves** menu (Open WebUI):

- **Default Brief Mode**: Choose your favorite (`rich`, `schematic`, `table`, `nano`).
- **Smart Nano Threshold**: Word count limit to trigger auto-Nano mode (Default: 300 words).
- **Target Lengths**: Customize how verbose the "Rich" report should be (Overview, Synthesis, Analysis word counts).
- **Task Model**: (Optional) Force a specific "smart" model (e.g., GPT-4o, Claude 3.5 Sonnet) to generate the Briefs, regardless of which model you are chatting with.

---

### 📌 Tips for Best Results

1.  **Isolation Mode**: When you trigger a Brief (`>>` or `??`), EasyBrief temporarily "blinds" the model to the previous chat history. This ensures the summary is 100% based on the specific text/search provided, preventing hallucinations from older messages.
2.  **Mermaid Diagrams**: Schematic and Rich modes use Mermaid.js. Ensure your Open WebUI interface supports Mermaid rendering (enabled by default in most versions).
3.  **Recursion**: You can chat *about* the Brief after it's generated. The Isolation Mode ends once the Brief is delivered.

---

### ‼️ Early Release
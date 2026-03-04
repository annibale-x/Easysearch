"""
title: Prototype
version: 0.0.23
author: Hannibal
https://github.com/annibale-x/open-webui-easybrief
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: WIP - Mermaid Stress Test Engine. Implemented strict header normalization for ER diagrams and expanded cardinality sanitization to fix hybrid pipe hallucinations (e.g. o|{).
"""

import re
from pydantic import BaseModel, Field
from typing import Optional

# Refined Prompt: More aggressive anchoring for micromodels, 18 tasks restored
EVALUATION_PROMPT = """You are a deterministic Mermaid generator. 
Your task is to generate EXACTLY 18 diagrams, following the order and the TYPE requested.
CRITICAL: Do not default to 'graph TD' if another type is requested.

--- CATEGORY: MINDMAP (Tasks 1-3) ---
1. Mindmap: The human central nervous system. (Use 'mindmap' syntax)
2. Mindmap: E-commerce website architecture. (Use 'mindmap' syntax)
3. Mindmap: Subfields of Artificial Intelligence. (Use 'mindmap' syntax)

--- CATEGORY: GRAPH TD (Tasks 4-6) ---
4. Graph TD: The process of a pedestrian crossing a street.
5. Graph TD: An online shopping checkout flow.
6. Graph TD: User login authentication process.

--- CATEGORY: GRAPH LR (Tasks 7-9) ---
7. Graph LR: A typical data engineering pipeline architecture.
8. Graph LR: Supply chain logistics from factory to consumer.
9. Graph LR: Microservices communication for a web app.

--- CATEGORY: ER DIAGRAM (Tasks 10-12) ---
10. ER Diagram: A library management system. (Use 'erDiagram' syntax)
11. ER Diagram: Hospital patient records. (Use 'erDiagram' syntax)
12. ER Diagram: University course enrollment. (Use 'erDiagram' syntax)

--- CATEGORY: PIE CHART (Tasks 13-15) ---
13. Pie Chart: Current web browser market share. (Use 'pie' syntax)
14. Pie Chart: Smartphone operating system distribution. (Use 'pie' syntax)
15. Pie Chart: Global renewable vs non-renewable energy sources. (Use 'pie' syntax)

--- CATEGORY: GANTT CHART (Tasks 16-18) ---
16. Gantt Chart: A 4-week software development lifecycle. (Use 'gantt' syntax)
17. Gantt Chart: Building a house. (Use 'gantt' syntax)
18. Gantt Chart: Planning and executing a marketing campaign. (Use 'gantt' syntax)

RULES:
- Start each block with exactly ```mermaid
- Follow the task numbering (1 to 18).
- Output ONLY the diagrams.
"""

FEW_SHOTS_TEMPLATE = """
--- EXAMPLES OF CORRECT SYNTAX ---
* graph TD
    A("Process Start") -->|"Initialize"| B{"Validation"}
    B -->|"Invalid?"| C["Wait / Retry"]
    C -->|"Re-check"| B
    B -->|"Valid?"| D["Core Execution!"]
    D --> E{"Integrity Check"}
    E -->|"Critical Error"| F["System Reset"]
    F --> A
    E -->|"Success"| G("End: Goal Reached")
* mindmap:
  root((Main))
    Branch
      Leaf
* erDiagram:
  ENTITY_A ||--o{ ENTITY_B : contains
  ENTITY_A {
    string id
    int count
  }
* pie:
  "Chrome" : 60
* gantt:
    title Project Timeline
    dateFormat YYYY-MM-DD
    section Phase 1
    Analysis      :a1, 2024-01-01, 5d
    Design        :a2, after a1, 3d
    section Phase 2
    Coding        :active, a3, after a2, 10d
    Test Milestone :milestone, m1, after a3, 0d
"""


class Filter:
    class UserValves(BaseModel):
        inject_few_shots: bool = Field(
            default=True,
            description="Injects Mermaid few-shots into the prompt to guide micromodels and reduce hallucinations.",
        )
        strip_styles: bool = Field(
            default=True,
            description="Removes model-hallucinated colors, styles, and classDefs to keep UI consistent.",
        )

    def __init__(self):
        """
        Initialize the MITM Filter with empty sessions and load valves.
        """
        self.valves = self.UserValves()
        self.sessions = {}

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Intercepts the incoming request to verify the trigger and reset session state.
        If trigger is active, it clears the history, evaluates valves, and injects the evaluation prompt.
        """
        user_id = __user__.get("id", "default") if __user__ else "default"

        # Total reset of the operating room
        self.sessions[user_id] = {
            "full_text": "",
            "is_inside": False,
            "buffer": "",
            "bypass": True,
        }

        messages = body.get("messages", [])

        if not messages:
            return body

        # Check for the magic trigger
        last_msg = str(messages[-1].get("content", "")).strip()

        if not last_msg.startswith("!x"):
            # Passthrough mode activated (Minimal invasiveness)
            return body

        # Trigger matched: Disable bypass
        self.sessions[user_id]["bypass"] = False

        # Prepare payload and evaluate the few-shots valve
        final_prompt = EVALUATION_PROMPT

        if self.valves.inject_few_shots:
            final_prompt += FEW_SHOTS_TEMPLATE

        # Clear history to avoid bias and inject the evaluation tasks prompt
        body["messages"] = [{"role": "user", "content": final_prompt}]

        return body

    def stream(self, event: dict, __user__: Optional[dict] = None) -> dict:
        """
        The core Man-in-the-Middle state machine for token streaming.
        O(1) passthrough if bypass is active.
        """
        user_id = __user__.get("id", "default") if __user__ else "default"

        # Setup safety session
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "full_text": "",
                "is_inside": False,
                "buffer": "",
                "bypass": True,
            }

        session = self.sessions[user_id]

        # O(1) Non-invasive passthrough
        if session["bypass"]:
            return event

        choices = event.get("choices", [])

        if not choices:
            return event

        content = choices[0].get("delta", {}).get("content", "")

        if not content:
            return event

        # 1. Update the global response memory
        session["full_text"] += content

        # 2. Mathematical State Calculation
        open_tags = session["full_text"].lower().count("```mermaid")
        all_tags = session["full_text"].count("```")
        close_tags = all_tags - open_tags

        # If we have more openings than closures, we are actively writing a diagram
        currently_inside = open_tags > close_tags

        # --- STATE TRANSITION MANAGEMENT ---

        # TRANSITION A: We just ENTERED a Mermaid block
        if currently_inside and not session["is_inside"]:
            session["is_inside"] = True
            session["buffer"] = ""
            # WATERMARK INJECTION: Append to the last piece of the word "mermaid"
            event["choices"][0]["delta"]["content"] = (
                content + "\n%% 💉 SANITIZED BY MITM 💉 %%\n"
            )
            return event

        # TRANSITION B: We just EXITED a Mermaid block
        if not currently_inside and session["is_inside"]:
            session["is_inside"] = False

            # Combine buffer and the completing chunk to resolve token fragmentation
            combined_text = session["buffer"] + content

            # Split exactly once to separate the diagram from the closing backticks
            parts = combined_text.split("```", 1)
            raw_mermaid = parts[0]
            remainder = parts[1] if len(parts) > 1 else ""

            # Apply Python sterilization, passing valves for conditional logic
            sanitized = self._sanitize_mermaid(raw_mermaid, self.valves)

            # Release the curated code followed by a rigidly reconstructed markdown closure
            event["choices"][0]["delta"]["content"] = sanitized + "\n```\n" + remainder
            session["buffer"] = ""
            return event

        # STATE C: We are INSIDE the block (Buffering)
        if session["is_inside"]:
            session["buffer"] += content
            event["choices"][0]["delta"]["content"] = ""  # Hide tokens from the UI
            return event

        # STATE D: We are OUTSIDE the block (Normal text)
        return event

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Post-processing hook. Ensures that if the stream is abruptly cut off,
        any trapped diagram in the buffer is safely sanitized and flushed.
        """
        user_id = __user__.get("id", "default") if __user__ else "default"

        if user_id in self.sessions:
            session = self.sessions[user_id]

            # Safety Flush: If the stream died while the cage was closed
            if (
                not session.get("bypass")
                and session.get("is_inside")
                and session.get("buffer")
            ):
                sanitized = self._sanitize_mermaid(session["buffer"], self.valves)

                messages = body.get("messages", [])

                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg.get("content"), str):
                        last_msg["content"] += "\n" + sanitized + "\n```\n"

            # Clean up the operating room
            del self.sessions[user_id]

        return body

    def _sanitize_mermaid(self, raw_code: str, valves: BaseModel) -> str:
        """
        Cleans and enforces Mermaid syntax.
        Routes to specific sanitizers based on graph type.
        """
        # Replace non-breaking spaces (\xa0) with standard spaces
        code = raw_code.replace("\xa0", " ").strip()
        code_lower = code.lower()

        if "mindmap" in code_lower:
            code = self._sterilize_mindmap(code)
        elif "graph " in code_lower:
            code = self._sterilize_graph(code, valves)
        elif "erdiagram" in code_lower:
            code = self._sterilize_er(code)
        elif "pie" in code_lower:
            code = self._sterilize_pie(code)
        elif "gantt" in code_lower:
            code = self._sterilize_gantt(code)

        return "\n" + code + "\n"

    def _sterilize_gantt(self, block: str) -> str:
        """
        Fixes Gantt charts corrupted by micromodels.
        Completely reassembles Task lines to ensure correct Mermaid parsing logic:
        [status], [id], [start_date | after id], [duration]
        """
        lines = block.split("\n")
        cleaned_lines = []

        # Pass 1: Re-assemble fragmented lines
        for line in lines:
            stripped = line.strip()

            if (
                not stripped
                or stripped.lower() in ["```mermaid", "```", "gantt"]
                or stripped.lower().startswith(
                    ("title ", "section ", "%%", "dateformat", "axisformat")
                )
            ):
                cleaned_lines.append(line)
                continue

            # If the line starts with a colon, it's a fragmented task data line
            if stripped.startswith(":"):
                if cleaned_lines and not cleaned_lines[-1].strip().lower().startswith(
                    (
                        "section",
                        "title",
                        "gantt",
                        "```",
                        "%%",
                        "dateformat",
                        "axisformat",
                    )
                ):
                    cleaned_lines[-1] = cleaned_lines[-1] + " " + stripped
                    continue

            # If the previous line ended with a colon, this line is probably the continuation
            if cleaned_lines and cleaned_lines[-1].strip().endswith(":"):
                if not stripped.lower().startswith(
                    (
                        "section",
                        "title",
                        "gantt",
                        "```",
                        "%%",
                        "dateformat",
                        "axisformat",
                    )
                ):
                    cleaned_lines[-1] = cleaned_lines[-1] + " " + stripped
                    continue

            cleaned_lines.append(line)

        # Pass 2: Clean up intra-line syntax using a universal re-assembler
        task_counter = 0
        for i, line in enumerate(cleaned_lines):
            stripped = line.strip()

            if not stripped or stripped.lower().startswith(
                ("gantt", "title ", "section ", "```", "%%", "dateformat", "axisformat")
            ):
                continue

            if line.count(":") >= 1:
                parts = line.split(":")
                title = " - ".join(p.strip() for p in parts[:-1]).strip()
                data = parts[-1].strip()

                # Eradicate hallucinated 'dur' prefixes
                data = re.sub(
                    r"\bdur\s+(\d+[smhdwM])", r"\1", data, flags=re.IGNORECASE
                )

                # Safe split of data properties
                if "," not in data:
                    raw_parts = data.split()
                else:
                    raw_parts = [p.strip() for p in data.split(",")]

                status_part = None
                id_part = None
                start_part = None
                duration_part = None

                # Dissect and categorize each property
                for p in raw_parts:
                    p = p.strip()
                    p_lower = p.lower()

                    if p_lower in ["active", "done", "crit", "milestone"]:
                        status_part = p_lower
                    elif re.match(r"^\d+[smhdwM]$", p):
                        duration_part = p
                    elif re.match(r"^\d{4}-\d{2}-\d{2}$", p):
                        try:
                            # Basic validation to prevent hallucinations like 2024-01-33
                            d_parts = p.split("-")
                            if (
                                1 <= int(d_parts[1]) <= 12
                                and 1 <= int(d_parts[2]) <= 31
                            ):
                                start_part = p
                        except:
                            pass
                    elif p_lower.startswith("after"):
                        if p_lower == "after":
                            start_part = "after_placeholder"  # Orphaned 'after' caught!
                        else:
                            start_part = p
                    else:
                        # Fallback for ID recognition
                        if not id_part and re.match(r"^[a-zA-Z0-9_]+$", p):
                            id_part = p

                task_counter += 1

                # Auto-assign missing IDs
                current_id = id_part if id_part else f"task{task_counter}"

                # Auto-chain missing or orphaned starts
                if start_part == "after_placeholder" or not start_part:
                    start_part = (
                        f"after task{task_counter-1}"
                        if task_counter > 1
                        else "2024-01-01"
                    )

                # Standardize durations (prevent crashes from empty durations)
                if not duration_part:
                    duration_part = "0d" if status_part == "milestone" else "1d"

                # Reassemble strictly in Mermaid Gantt format
                new_data_parts = []
                if status_part:
                    new_data_parts.append(status_part)
                new_data_parts.append(current_id)
                new_data_parts.append(start_part)
                new_data_parts.append(duration_part)

                new_data = ", ".join(new_data_parts)
                indent = line[: len(line) - len(line.lstrip())]
                cleaned_lines[i] = f"{indent}{title} : {new_data}"

        return "\n".join(cleaned_lines)

    def _sterilize_pie(self, block: str) -> str:
        """
        Fixes Pie charts corrupted by syntax hallucinations.
        Converts assignment operators '=' to ':' and extracts labels
        from hallucinated graph node syntax (e.g., ID[Label] : value).
        """
        lines = block.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            if (
                not stripped
                or stripped.lower() in ["```mermaid", "```", "pie"]
                or stripped.lower().startswith("title ")
            ):
                cleaned_lines.append(line)
                continue

            if ":" in stripped or "=" in stripped:
                normalized = stripped.replace("=", ":")
                parts = normalized.split(":", 1)
                raw_label = parts[0].strip()
                value = parts[1].strip()

                node_match = re.match(
                    r'^[A-Za-z0-9_]*\s*[\[\(]\s*"?([^"\]\)]+)"?\s*[\]\)]$', raw_label
                )

                if node_match:
                    raw_label = node_match.group(1).strip()

                raw_label = raw_label.strip("\"'")

                indent = line[: len(line) - len(line.lstrip())]
                line = f'{indent}"{raw_label}" : {value}'

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _sterilize_er(self, block: str) -> str:
        """
        Fixes ER diagrams corrupted by 'graph' syntax hallucinations,
        UML class syntax hallucinations, glued relationships, and relationships
        hallucinated inside attribute blocks.
        """
        lines = block.split("\n")
        cleaned_lines = []
        in_entity_block = False

        for line in lines:
            stripped = line.strip()
            lower_stripped = stripped.lower()

            if (
                not stripped
                or lower_stripped in ["```mermaid", "```"]
                or lower_stripped.startswith("title ")
                or lower_stripped.startswith("%%")
            ):
                cleaned_lines.append(line)
                continue

            # Force strict normalization of the ER diagram declaration line
            if lower_stripped.startswith("erdiagram"):
                cleaned_lines.append("erDiagram")
                continue

            # Fix hallucinated sequence/flowchart AND UML inheritance arrows (e.g. -->>, ->, ---|>)
            line = re.sub(
                r"([A-Za-z0-9_]+)\s*(?:-->>|-->|->|-\.>|\.\.>|=>|==>|-{1,3}\|>)\s*([A-Za-z0-9_]+)",
                r"\1 ||--o{ \2",
                line,
            )

            # Fix hallucinated mixed-line relations (e.g. ||--|..|) containing both solid and dashed elements
            line = re.sub(
                r"([A-Za-z0-9_]+)\s*(?:[\}o\|]*--[\}o\|]*\.\.[\}o\|]*|[\}o\|]*\.\.[\}o\|]*--[\}o\|]*)\s*([A-Za-z0-9_]+)",
                r"\1 ||--o{ \2",
                line,
            )

            is_relationship = bool(re.search(r"[\}o\|]*(?:--|\.\.)[o\|\{]*", line))

            if is_relationship:
                if in_entity_block:
                    indent = line[: len(line) - len(line.lstrip())]
                    cleaned_lines.append(indent + "}")
                    in_entity_block = False

                def _clean_entity(match):
                    entity_name = match.group(2)
                    return re.sub(r"\s+", "_", entity_name.strip())

                line = re.sub(
                    r'([A-Za-z0-9_]+)\s*[\[\(]\s*"?([^"\]\)]+)"?[\]\)]?',
                    _clean_entity,
                    line,
                )

                line = re.sub(r"([\}o\|]+)\s*(--|\.\.)\s*([o\|\{]+)", r"\1\2\3", line)

                # Extended fix for hallucinated extra pipes and hybrid cardinalities
                for bad, good in [
                    ("}||", "}|"),
                    ("||{", "|{"),
                    ("}o|", "}o"),
                    ("|o{", "o{"),
                    ("o|{", "o{"),
                    ("}|o", "}o"),
                    ("o||", "o|"),
                    ("||o", "|o"),
                ]:
                    line = line.replace(bad, good)

                line = re.sub(
                    r"([A-Za-z0-9_]+)\s*([\}o\|]*(?:--|\.\.)[o\|\{]*)\s*([A-Za-z0-9_]+)",
                    r"\1 \2 \3",
                    line,
                )

                # Fix unquoted relationship labels with spaces or force missing labels
                if ":" not in line:
                    line = line.rstrip() + " : relates_to"
                else:
                    parts = line.split(":", 1)
                    rel_label = parts[1].strip().strip("\"'")
                    rel_label = re.sub(r"\s+", "_", rel_label)
                    if not rel_label:
                        rel_label = "relates_to"
                    line = f"{parts[0].rstrip()} : {rel_label}"

                cleaned_lines.append(line)
                continue

            if "{" in stripped:
                in_entity_block = True

            is_closing = "}" in stripped

            if in_entity_block and "{" not in stripped and not is_closing:
                if any(
                    x in lower_stripped
                    for x in ["one-to-", "many-to-", "1:n", "n:m", "1:1", "->", "<-"]
                ):
                    continue

                if ":" in stripped:
                    m = re.match(
                        r"^(\s*)([a-zA-Z0-9_]+)\s*:\s*([a-zA-Z0-9_]+)\s*$", line
                    )
                    if m:
                        line = f"{m.group(1)}{m.group(3)} {m.group(2)}"
                    else:
                        continue

                line = re.sub(r"^(\s*)[\+\-\~]\s*", r"\1", line)
                line = re.sub(
                    r"^(\s*)([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\s*$", r"\1\3 \2", line
                )

                cleaned_lines.append(line)

                if is_closing:
                    in_entity_block = False
                continue

            if is_closing:
                in_entity_block = False

            title_match = re.match(
                r'^[A-Za-z0-9_]*\s*[\[\(]\s*"?([^"\]\)]+)"?[\]\)]?$', stripped
            )

            if title_match:
                cleaned_lines.append(f'title "{title_match.group(1).strip()}"')
                continue

            cleaned_lines.append(line)

        if in_entity_block:
            cleaned_lines.append("}")

        return "\n".join(cleaned_lines)

    def _sterilize_mindmap(self, block: str) -> str:
        """
        Smart sanitizer for Mermaid mindmaps.
        """
        lines = block.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            lower_stripped = stripped.lower()

            if lower_stripped in ["```mermaid", "```"] or not stripped:
                cleaned_lines.append(line)
                continue

            if lower_stripped.startswith("mindmap"):
                cleaned_lines.append("mindmap")
                continue

            if stripped.startswith("root(") or stripped.startswith("root(("):
                cleaned_lines.append(line)
                continue

            indent = line[: len(line) - len(stripped)]
            safe_text = re.sub(r"^(?:[\|\+\-\*\>]\s*)+", "", stripped)

            if not safe_text:
                continue

            safe_text = re.sub(r"(\*\*|__|\*)", "", safe_text)
            safe_text = safe_text.replace('"', "")
            safe_text = re.sub(r"[\(\[\{]", ' "', safe_text)
            safe_text = re.sub(r"[\)\]\}]", '" ', safe_text)
            safe_text = re.sub(r'("\s*")+', '"', safe_text)
            safe_text = re.sub(r"\s+", " ", safe_text).strip()

            cleaned_lines.append(f"{indent}{safe_text}")

        data_lines_info = []
        for i, line in enumerate(cleaned_lines):
            stripped = line.strip()
            if stripped and stripped.lower() not in ["```mermaid", "```", "mindmap"]:
                indent_len = len(line) - len(stripped)
                data_lines_info.append((i, indent_len))

        if data_lines_info:
            min_indent = min(info[1] for info in data_lines_info)
            root_count = sum(1 for info in data_lines_info if info[1] == min_indent)

            if root_count > 1:
                first_idx = data_lines_info[0][0]
                master_indent = " " * max(0, min_indent - 2)
                cleaned_lines.insert(first_idx, f"{master_indent}root((Core Concept))")

                for i in range(first_idx + 1, len(cleaned_lines)):
                    line = cleaned_lines[i]
                    stripped = line.strip()
                    if stripped and stripped.lower() not in [
                        "```mermaid",
                        "```",
                        "mindmap",
                    ]:
                        cleaned_lines[i] = "  " + line

        return "\n".join(cleaned_lines)

    def _sterilize_graph(self, block: str, valves: BaseModel) -> str:
        """
        Fixes common trailing character hallucinations, space-in-ID issues,
        naked quoted nodes, and style stripping.
        """
        block = re.sub(
            r'graph_([a-zA-Z]{2})\s*\[\s*[\'"]graph\s+[a-zA-Z]{2}[\'"]\s*\]',
            r"graph \1",
            block,
            flags=re.IGNORECASE,
        )

        safe_block = re.sub(r'(\["[^"\]]+"\])\)', r"\1", block)
        safe_block = re.sub(r'(\("[^"\)]+"\))\]', r"\1", safe_block)

        safe_block = re.sub(
            r'-->\s*\|\s*"?([^|\]"]+)"?\s*\]',
            lambda m: f'-->NODE_{re.sub(r"[^a-zA-Z0-9]", "", m.group(1))[:10]}["{m.group(1)}"]',
            safe_block,
        )

        lines = safe_block.split("\n")
        cleaned_lines = []
        reserved_keywords = {
            "end",
            "subgraph",
            "click",
            "style",
            "class",
            "classdef",
            "linkstyle",
        }

        def _clean_node_part(work_part: str) -> str:
            work_part = work_part.strip()
            work_part = re.sub(r"(\*\*|__|\*)", "", work_part)

            for opener, closer in [("[", "]"), ("(", ")"), ("{", "}")]:
                if work_part.endswith(closer) and opener not in work_part:
                    work_part = work_part[:-1].strip()

            if (
                work_part.startswith('"')
                and work_part.endswith('"')
                and len(work_part) > 1
            ):
                inner_text = work_part[1:-1].strip()
                safe_gen_id = "N_" + re.sub(r"[^a-zA-Z0-9]", "", inner_text)[:10]
                return f'{safe_gen_id}["{inner_text}"]'

            node_match = re.match(r"^([^\[\(\{]+?)\s*([\[\(\{].*)?$", work_part)

            if node_match:
                raw_id = node_match.group(1).strip()
                label_block = node_match.group(2) or ""

                if label_block:
                    opener = label_block[0]
                    bracket_map = {"[": "]", "(": ")", "{": "}"}
                    if opener in bracket_map:
                        expected_closer = bracket_map[opener]
                        if not label_block.endswith(expected_closer):
                            label_block = (
                                label_block.rstrip(")]}\"' ") + expected_closer
                            )

                if not label_block and " " in raw_id:
                    safe_id = re.sub(r"[^a-zA-Z0-9_]", "", re.sub(r"\s+", "_", raw_id))
                    if safe_id.lower() in reserved_keywords:
                        safe_id = f"ID_{safe_id}"
                    if not safe_id:
                        safe_id = "NODE"
                    return f'{safe_id}["{raw_id}"]'

                raw_id = raw_id.replace('"', "")
                safe_id = re.sub(r"\s+", "_", raw_id)
                safe_id = re.sub(r"[^a-zA-Z0-9_]", "", safe_id)

                if not safe_id:
                    safe_id = "NODE"

                if safe_id.lower() in reserved_keywords:
                    safe_id = f"ID_{safe_id}"

                return safe_id + label_block

            return work_part

        for line in lines:
            stripped = line.strip()
            lower_stripped = stripped.lower()

            if (
                not stripped
                or lower_stripped in ["```mermaid", "```"]
                or lower_stripped.startswith("graph ")
                or lower_stripped.startswith("%%")
            ):
                cleaned_lines.append(line)
                continue

            is_style_line = lower_stripped.startswith(
                ("style ", "classdef ", "click ", "linkstyle ", "class ")
            )

            if is_style_line:
                if getattr(valves, "strip_styles", True):
                    continue
                else:
                    cleaned_lines.append(line)
                    continue

            if lower_stripped.startswith("subgraph ") or lower_stripped == "end":
                cleaned_lines.append(line)
                continue

            leading_spaces = line[: len(line) - len(line.lstrip())]

            if "-->" in line:
                parts = line.split("-->")
                new_parts = []

                for i, part in enumerate(parts):
                    work_part = part.strip()
                    has_semi = work_part.endswith(";")

                    if has_semi:
                        work_part = work_part[:-1].strip()

                    edge_label = ""
                    m1 = re.match(r'^\|\s*"([^"]+)"\s*\|?(.*)', work_part)
                    m2 = re.match(r"^\|([^|]+)\|(.*)", work_part)

                    if m1:
                        clean_inner = m1.group(1).strip()
                        if clean_inner:
                            clean_inner = re.sub(r"(\*\*|__|\*)", "", clean_inner)
                            edge_label = f'|"{clean_inner}"|'
                        work_part = m1.group(2).strip()
                    elif m2:
                        clean_inner = m2.group(1).strip()
                        if clean_inner:
                            clean_inner = re.sub(r"(\*\*|__|\*)", "", clean_inner)
                            edge_label = f'|"{clean_inner}"|'
                        work_part = m2.group(2).strip()

                    cleaned_node = _clean_node_part(work_part)
                    reconstructed = edge_label + cleaned_node

                    if has_semi and i == len(parts) - 1:
                        reconstructed += ";"

                    if i == 0:
                        new_parts.append(leading_spaces + reconstructed)
                    else:
                        new_parts.append(reconstructed)

                cleaned_lines.append("-->".join(new_parts))

            else:
                has_semi = stripped.endswith(";")
                work_part = stripped[:-1].strip() if has_semi else stripped
                cleaned_node = _clean_node_part(work_part)

                if has_semi:
                    cleaned_node += ";"

                cleaned_lines.append(leading_spaces + cleaned_node)

        return "\n".join(cleaned_lines)

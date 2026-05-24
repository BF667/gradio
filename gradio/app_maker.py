"""
Gradio Sketch — Visual no-code app builder with Vibe Mode (AI chat).

Inspired by Gradio 5 Sketch + Gradio --vibe. Build Gradio apps visually
with a flow-based canvas, or describe what you want in natural language
and let AI generate the code for you.

Usage:
    from gradio import app_maker

    demo = app_maker()
    demo.launch()

Or with options:
    demo = app_maker(options={
        "components": ["Textbox", "Slider", "Button", "Image", "Dropdown"],
        "theme": "soft",
        "title": "My App Builder",
        "vibe": True
    })
    demo.launch()
"""

from __future__ import annotations

import json
import os
import secrets
import difflib
import tempfile
from pathlib import Path
from typing import Any

from gradio.blocks import Blocks
from gradio.components import Button, Code, Textbox
from gradio.components.appmaker import AppMaker, _default_components
from gradio.layouts import Row, Column


def _generate_code_from_schema(schema: dict) -> str:
    """Generate Gradio Blocks Python code from a Gradio Sketch schema."""
    registry = _default_components()
    layout = schema.get("layout", {})
    events = schema.get("events", [])

    # Collect all component nodes for variable naming
    component_vars: dict[str, str] = {}

    def collect_vars(node: dict, counter: list[int]):
        if node.get("kind") == "component":
            comp_type = node.get("type", "Component")
            var_name = comp_type.lower() + str(counter[0])
            counter[0] += 1
            component_vars[node.get("id", "")] = var_name
        elif node.get("kind") == "layout":
            for child in node.get("children", []):
                collect_vars(child, counter)

    collect_vars(layout, [1])

    # Generate event handler functions
    lines = ["import gradio as gr", ""]

    for evt in events:
        fn_name = evt.get("fn_name", "handler")
        inputs = evt.get("inputs", [])
        outputs = evt.get("outputs", [])
        inp_vars = [component_vars.get(i, i) for i in inputs]
        out_vars = [component_vars.get(o, o) for o in outputs]
        lines.append(f"def {fn_name}({', '.join(inp_vars)}):")
        lines.append("    # TODO: Implement this function")
        if out_vars:
            lines.append(f"    return {', '.join(out_vars)}")
        else:
            lines.append("    return None")
        lines.append("")

    # Generate layout code
    lines.append("with gr.Blocks() as demo:")

    def render_node(node: dict, indent: int):
        pad = "    " * indent
        kind = node.get("kind", "")
        ntype = node.get("type", "")
        props = node.get("props", {})
        nid = node.get("id", "")

        if kind == "layout":
            if ntype == "row":
                lines.append(f"{pad}with gr.Row():")
            elif ntype == "column":
                scale = props.get("scale", 1)
                lines.append(f"{pad}with gr.Column(scale={scale}):")
            elif ntype == "tabs":
                lines.append(f"{pad}with gr.Tabs():")
            elif ntype == "tabitem":
                label = props.get("label", "Tab")
                lines.append(f'{pad}with gr.Tab("{label}"):')
            elif ntype == "accordion":
                label = props.get("label", "Advanced")
                open_val = props.get("open", False)
                lines.append(f'{pad}with gr.Accordion("{label}", open={open_val}):')
            elif ntype == "group":
                lines.append(f"{pad}with gr.Group():")

            for child in node.get("children", []):
                render_node(child, indent + 1)

        elif kind == "component":
            var = component_vars.get(nid, ntype.lower())
            reg = registry.get(ntype)
            if reg:
                try:
                    code_str = reg["code"].format(**props)
                    lines.append(f"{pad}{var} = gr.{code_str}")
                except (KeyError, IndexError):
                    label = props.get("label", ntype)
                    lines.append(f'{pad}{var} = gr.{ntype}(label="{label}")')
            else:
                label = props.get("label", ntype)
                lines.append(f'{pad}{var} = gr.{ntype}(label="{label}")')

    if layout:
        render_node(layout, 1)

    # Wire up events
    for evt in events:
        source_id = evt.get("source_id", "")
        event_name = evt.get("event", "click")
        fn_name = evt.get("fn_name", "handler")
        inputs = evt.get("inputs", [])
        outputs = evt.get("outputs", [])
        source_var = component_vars.get(source_id, source_id)
        inp_vars = [component_vars.get(i, i) for i in inputs]
        out_vars = [component_vars.get(o, o) for o in outputs]
        if source_var:
            lines.append(
                f"    {source_var}.{event_name}({fn_name}, "
                f"inputs=[{', '.join(inp_vars)}], "
                f"outputs=[{', '.join(out_vars)}])"
            )

    lines.append("")
    lines.append("demo.launch()")
    return "\n".join(lines)


def _vibe_generate_code(prompt: str, current_code: str) -> dict:
    """
    Use AI to generate Gradio code from a natural language prompt.
    Mirrors the gradio --vibe functionality.
    Returns dict with: code, reasoning, diff_stats
    """
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        return {
            "code": current_code,
            "reasoning": "Error: huggingface_hub not installed. Install with: pip install huggingface_hub",
            "diff_stats": {"lines_added": 0, "lines_removed": 0},
        }

    try:
        client = InferenceClient()
    except Exception:
        return {
            "code": current_code,
            "reasoning": "Error: Could not initialize HuggingFace InferenceClient. Make sure you're logged in with `huggingface-cli login`",
            "diff_stats": {"lines_added": 0, "lines_removed": 0},
        }

    system_prompt = """You are a Gradio code generator. Given an existing Gradio app and a natural language prompt, \
return the FULL new code for the Gradio app. Always return the complete code inside a ```python code block. \
Follow Gradio best practices: use gr.Blocks for layout, proper component types, and wire up events correctly. \
If the prompt asks to add components, add them to the appropriate layout container. \
If the prompt asks to modify the app, make the requested changes while preserving the rest."""

    user_prompt = f"""Existing code:
```python
{current_code}
```

Prompt:
{prompt}

Return the complete new Gradio app code."""

    try:
        response = client.chat_completion(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=10000,
        )
        content = response.choices[0].message.content or ""
    except Exception as e:
        return {
            "code": current_code,
            "reasoning": f"Error generating code: {str(e)}",
            "diff_stats": {"lines_added": 0, "lines_removed": 0},
        }

    # Extract reasoning (think blocks)
    reasoning = ""
    if "<think" in content:
        try:
            think_start = content.index("<think") 
            think_end = content.index("</think") 
            reasoning = content[think_start:think_end].split(">", 1)[-1].strip()
            content = content[:think_start] + content[think_end + len("</think"):]
            if content.startswith(">"):
                content = content[1:]
        except (ValueError, IndexError):
            pass

    # Extract code from markdown block
    code = content
    if "```python\n" in content:
        try:
            start = content.index("```python\n") + len("```python\n")
            end = content.find("\n```", start)
            code = content[start:end] if end != -1 else content[start:]
        except ValueError:
            pass
    elif "```\n" in content:
        try:
            start = content.index("```\n") + len("```\n")
            end = content.find("\n```", start)
            code = content[start:end] if end != -1 else content[start:]
        except ValueError:
            pass

    # Calculate diff stats
    original_lines = current_code.splitlines(keepends=True)
    new_lines = code.splitlines(keepends=True)
    diff = list(difflib.unified_diff(original_lines, new_lines, n=0))
    lines_added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    lines_removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

    return {
        "code": code,
        "reasoning": reasoning or "Done.",
        "diff_stats": {"lines_added": lines_added, "lines_removed": lines_removed},
    }


def app_maker(options: dict[str, Any] | None = None) -> Blocks:
    """
    Create a visual no-code Gradio app builder (Gradio Sketch) with Vibe Mode.

    Design Gradio apps visually with a flow-based canvas, layout containers
    (Row, Column, Tabs, Accordion), component palette, event wiring, and
    code generation. Includes a Vibe Mode AI chat panel (like gradio --vibe)
    that lets you describe changes in natural language.

    Parameters:
        options: Configuration dictionary with optional keys:
            - components: List of component type names to include.
            - theme: Gradio theme name. Default: "soft".
            - title: Title for the builder. Default: "Gradio Sketch".
            - vibe: Enable Vibe Mode AI chat. Default: True.

    Returns:
        A Gradio Blocks object containing the visual builder UI.
    """
    opts = options or {}
    available_components = opts.get("components", None)
    theme_name = opts.get("theme", "soft")
    title = opts.get("title", "Gradio Sketch")
    vibe_enabled = opts.get("vibe", True)

    # Build the component registry, optionally filtering
    if available_components:
        full_registry = _default_components()
        filtered_registry = {
            k: v for k, v in full_registry.items() if k in available_components
        }
    else:
        filtered_registry = None  # Use defaults in the component

    with Blocks(title=title, fill_height=True, theme=theme_name) as demo:
        # The main AppMaker Svelte component
        maker = AppMaker(
            components=filtered_registry,
            title=title,
            dark_mode=True,
            min_height=700,
        )

        with Row():
            generate_btn = Button("✨ Generate Code", variant="primary", size="lg")

        output_code = Code(
            label="Generated Gradio Code",
            language="python",
            interactive=True,
            lines=20,
        )

        # ── Vibe Mode: AI chat for natural language code generation ──
        vibe_prompt = Textbox(
            label="Vibe Mode — Describe what you want",
            placeholder="e.g. 'Add a chatbot with a text input and send button' or 'Change the theme to soft'",
            lines=2,
            visible=vibe_enabled,
            scale=3,
        )
        vibe_btn = Button(
            "🚀 Vibe",
            variant="secondary",
            visible=vibe_enabled,
            scale=1,
        )

        # Track vibe history for undo
        vibe_history: list[dict] = []

        def on_generate(schema_json: str) -> str:
            """When the AppMaker generates a schema, produce Gradio code."""
            schema = {"layout": {}, "events": []}
            if isinstance(schema_json, str):
                try:
                    schema = json.loads(schema_json)
                except (ValueError, TypeError):
                    pass
            elif isinstance(schema_json, dict):
                schema = schema_json
            return _generate_code_from_schema(schema)

        def on_generate_btn_click(schema_json: str) -> str:
            return on_generate(schema_json)

        def on_vibe(prompt: str, current_code: str) -> tuple[str, str]:
            """Vibe mode: generate code from natural language prompt."""
            if not prompt or not prompt.strip():
                return current_code, "Please enter a description of what you want."

            # Save current state for undo
            vibe_history.append({"code": current_code, "prompt": prompt})

            result = _vibe_generate_code(prompt, current_code)
            new_code = result["code"]
            reasoning = result["reasoning"]
            stats = result["diff_stats"]

            summary = reasoning
            if stats["lines_added"] > 0 or stats["lines_removed"] > 0:
                summary += f"\n\n(+{stats['lines_added']} lines, -{stats['lines_removed']} lines)"

            return new_code, summary

        def on_vibe_undo() -> str:
            """Undo the last vibe edit."""
            if not vibe_history:
                return "Nothing to undo."
            last = vibe_history.pop()
            return last["code"]

        # Wire up events
        maker.generate(on_generate, inputs=[maker], outputs=[output_code])
        generate_btn.click(
            on_generate_btn_click,
            inputs=[maker],
            outputs=[output_code],
        )

        if vibe_enabled:
            vibe_btn.click(
                on_vibe,
                inputs=[vibe_prompt, output_code],
                outputs=[output_code, vibe_prompt],
            )

    return demo

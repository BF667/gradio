"""
Gradio App Maker — Visual free-form drag-and-drop app builder.

Usage:
    from gradio import app_maker

    demo = app_maker()
    demo.launch()

Or with options:
    demo = app_maker(options={
        "components": ["Textbox", "Slider", "Button", "Image", "Dropdown"],
        "theme": "soft",
        "title": "My App Builder"
    })
    demo.launch()

The result is a Gradio Blocks object that contains the visual builder UI.
When you design an app in the builder, it generates runnable Gradio Blocks code.
Components can be freely moved anywhere on the canvas.
"""

from __future__ import annotations

import json
from typing import Any

from gradio.blocks import Blocks
from gradio.components import Button, Code
from gradio.components.appmaker import AppMaker, _default_components
from gradio.layouts import Row


def _generate_code(schema: dict) -> str:
    """Generate Gradio Blocks Python code from a schema."""
    registry = _default_components()
    lines = ["import gradio as gr", ""]
    lines.append("with gr.Blocks() as demo:")

    items = schema.get("layout", [])
    # Sort by y then x for code order (top-to-bottom, left-to-right)
    sorted_items = sorted(items, key=lambda c: (c.get("y", 0), c.get("x", 0)))

    for item in sorted_items:
        comp_type = item.get("type", "Textbox")
        props = item.get("props", {})
        if comp_type in registry:
            try:
                lines.append("    " + registry[comp_type]["code"].format(**props))
            except (KeyError, IndexError):
                lines.append(f'    gr.{comp_type}(label="{props.get("label", comp_type)}")')
        else:
            lines.append(f'    gr.{comp_type}(label="{props.get("label", comp_type)}")')

    lines.append("")
    lines.append("demo.launch()")
    return "\n".join(lines)


def app_maker(options: dict[str, Any] | None = None) -> Blocks:
    """
    Create a visual free-form drag-and-drop Gradio app builder.

    Components can be placed anywhere on the canvas and moved freely.
    Add components from the sidebar, the floating + button, or by clicking.

    Parameters:
        options: Configuration dictionary with optional keys:
            - components: List of component type names to include.
            - theme: Gradio theme name. Default: "soft".
            - title: Title for the builder. Default: "App Maker".

    Returns:
        A Gradio Blocks object containing the visual builder UI.
    """
    opts = options or {}
    available_components = opts.get("components", None)
    theme_name = opts.get("theme", "soft")
    title = opts.get("title", "App Maker")

    # Build the component registry, optionally filtering
    if available_components:
        full_registry = _default_components()
        filtered_registry = {
            k: v for k, v in full_registry.items() if k in available_components
        }
    else:
        filtered_registry = None  # Use defaults in the component

    with Blocks(title=title, fill_height=True) as demo:
        # The main AppMaker Svelte component
        maker = AppMaker(
            components=filtered_registry,
            title=title,
            min_height=700,
        )

        with Row():
            generate_btn = Button("✨ Generate Gradio Code", variant="primary", size="lg")

        output_code = Code(
            label="Generated Gradio Code",
            language="python",
            interactive=True,
            lines=20,
        )

        def on_generate(schema_json: str) -> str:
            """When the AppMaker generates a schema, produce Gradio code."""
            schema = {"layout": []}
            if isinstance(schema_json, str):
                try:
                    schema = json.loads(schema_json)
                except (ValueError, TypeError):
                    pass
            elif isinstance(schema_json, dict):
                schema = schema_json
            return _generate_code(schema)

        # The Svelte component fires "generate" event with the schema JSON
        # inputs=[maker] so the component's value (schema JSON) is passed to the callback
        maker.generate(on_generate, inputs=[maker], outputs=[output_code])

        # The button also triggers code generation from current state
        def on_generate_btn_click(schema_json: str) -> str:
            return on_generate(schema_json)

        generate_btn.click(
            on_generate_btn_click,
            inputs=[maker],
            outputs=[output_code],
        )

    return demo

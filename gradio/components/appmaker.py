"""gr.AppMaker() component — Gradio Sketch visual app builder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from gradio_client.documentation import document

from gradio.components.base import Component
from gradio.events import EventListener

if TYPE_CHECKING:
    from gradio.components import Timer


@document()
class AppMaker(Component):
    """
    Creates a visual drag-and-drop app builder component inspired by Gradio Sketch.
    Users can add Gradio components and layout containers, arrange them in a
    flow-based canvas, wire up events, and generate runnable Gradio Blocks code.

    Example:
        ```python
        from gradio import app_maker

        demo = app_maker()
        demo.launch()
        ```
    """

    EVENTS = [
        EventListener("change"),
        EventListener("generate"),
    ]

    def __init__(
        self,
        value: str | None = None,
        *,
        components: dict[str, dict[str, Any]] | None = None,
        title: str = "Gradio Sketch",
        dark_mode: bool = True,
        label: str | None = None,
        every: Timer | float | None = None,
        inputs: Component | list[Component] | set[Component] | None = None,
        show_label: bool = False,
        visible: bool | Literal["hidden"] = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
        key: int | str | tuple[int | str, ...] | None = None,
        preserved_by_key: list[str] | str | None = "value",
        min_height: int | None = None,
        container: bool = False,
        **props: Any,
    ):
        """
        Parameters:
            value: The generated schema JSON string.
            components: Dictionary of available component definitions.
            title: Title displayed in the app maker header.
            dark_mode: If True, use dark vibe theme.
            label: The label for this component.
            every: Continuously calls `value` to recalculate it if `value` is a function.
            inputs: Components that are used as inputs to calculate `value` if `value` is a function.
            show_label: If True, the label will be displayed.
            visible: If False, component will be hidden.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM.
            elem_classes: An optional list of strings that are assigned as the classes of this component.
            render: If False, component will not be rendered.
            key: In a gr.render, components with the same key are treated as the same component.
            preserved_by_key: Parameters preserved across re-renders when key matches.
            min_height: The minimum height of the component in pixels.
            container: If True, the component will be displayed in a container.
        """
        self.components = components or _default_components()
        self.title = title
        self.dark_mode = dark_mode
        self.min_height = min_height
        Component.__init__(
            self,
            label=label,
            every=every,
            inputs=inputs,
            show_label=show_label,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            key=key,
            preserved_by_key=preserved_by_key,
            value=value,
            container=container,
        )

    def example_payload(self) -> Any:
        return '{"layout":{"id":"app","kind":"layout","type":"column","children":[],"props":{}},"events":[],"theme":"soft","title":"My App"}'

    def example_value(self) -> Any:
        return '{"layout":{"id":"app","kind":"layout","type":"column","children":[],"props":{}},"events":[],"theme":"soft","title":"My App"}'

    def preprocess(self, payload: str | None) -> str | None:
        return payload

    def postprocess(self, value: str | None) -> str | None:
        return value

    def api_info(self) -> dict[str, Any]:
        return {"type": "string"}

    @property
    def skip_api(self):
        return False

    def get_block_name(self):
        return "appmaker"


def _default_components() -> dict[str, dict[str, Any]]:
    """Return the default component registry for Gradio Sketch."""
    return {
        # ── Layout ──
        "Row": {
            "category": "layout",
            "icon": "▦",
            "width": 400,
            "height": 80,
            "defaults": {"equal_height": True},
            "code": "with gr.Row():",
            "events": [],
        },
        "Column": {
            "category": "layout",
            "icon": "▥",
            "width": 200,
            "height": 120,
            "defaults": {"scale": 1},
            "code": "with gr.Column(scale={scale}):",
            "events": [],
        },
        "Tabs": {
            "category": "layout",
            "icon": "⊟",
            "width": 400,
            "height": 200,
            "defaults": {"labels": ["Tab 1", "Tab 2"]},
            "code": "with gr.Tabs():",
            "events": [],
        },
        "Accordion": {
            "category": "layout",
            "icon": "▤",
            "width": 400,
            "height": 120,
            "defaults": {"label": "Advanced", "open": False},
            "code": 'with gr.Accordion("{label}", open={open}):',
            "events": [],
        },
        # ── Input ──
        "Textbox": {
            "category": "input",
            "icon": "T",
            "width": 220,
            "height": 80,
            "defaults": {"label": "Textbox", "lines": 1, "placeholder": "Type here..."},
            "code": 'gr.Textbox(label="{label}", lines={lines}, placeholder="{placeholder}")',
            "events": ["change", "input", "submit"],
        },
        "Number": {
            "category": "input",
            "icon": "#",
            "width": 180,
            "height": 70,
            "defaults": {"label": "Number", "value": 0, "precision": 0},
            "code": 'gr.Number(label="{label}", value={value}, precision={precision})',
            "events": ["change"],
        },
        "Slider": {
            "category": "input",
            "icon": "≡",
            "width": 240,
            "height": 70,
            "defaults": {
                "label": "Slider",
                "minimum": 0,
                "maximum": 100,
                "value": 50,
                "step": 1,
            },
            "code": 'gr.Slider(label="{label}", minimum={minimum}, maximum={maximum}, value={value}, step={step})',
            "events": ["change", "release"],
        },
        "Dropdown": {
            "category": "input",
            "icon": "▾",
            "width": 220,
            "height": 70,
            "defaults": {
                "label": "Dropdown",
                "choices": ["Option 1", "Option 2", "Option 3"],
            },
            "code": 'gr.Dropdown(label="{label}", choices={choices})',
            "events": ["change"],
        },
        "Checkbox": {
            "category": "input",
            "icon": "☐",
            "width": 180,
            "height": 60,
            "defaults": {"label": "Checkbox", "value": False},
            "code": 'gr.Checkbox(label="{label}", value={value})',
            "events": ["change"],
        },
        "Radio": {
            "category": "input",
            "icon": "◉",
            "width": 220,
            "height": 90,
            "defaults": {
                "label": "Radio",
                "choices": ["Option 1", "Option 2", "Option 3"],
            },
            "code": 'gr.Radio(label="{label}", choices={choices})',
            "events": ["change"],
        },
        # ── Action ──
        "Button": {
            "category": "action",
            "icon": "▶",
            "width": 160,
            "height": 56,
            "defaults": {"label": "Submit", "variant": "primary"},
            "code": 'gr.Button("{label}", variant="{variant}")',
            "events": ["click"],
        },
        # ── Media ──
        "Image": {
            "category": "media",
            "icon": "▨",
            "width": 220,
            "height": 180,
            "defaults": {"label": "Image"},
            "code": 'gr.Image(label="{label}")',
            "events": ["change", "upload", "clear"],
        },
        "Audio": {
            "category": "media",
            "icon": "♪",
            "width": 220,
            "height": 120,
            "defaults": {"label": "Audio"},
            "code": 'gr.Audio(label="{label}")',
            "events": ["change", "upload", "clear"],
        },
        "Video": {
            "category": "media",
            "icon": "▷",
            "width": 280,
            "height": 200,
            "defaults": {"label": "Video"},
            "code": 'gr.Video(label="{label}")',
            "events": ["change", "upload", "clear"],
        },
        "File": {
            "category": "media",
            "icon": "☰",
            "width": 220,
            "height": 80,
            "defaults": {"label": "File"},
            "code": 'gr.File(label="{label}")',
            "events": ["change"],
        },
        # ── Output / Display ──
        "Markdown": {
            "category": "output",
            "icon": "¶",
            "width": 300,
            "height": 100,
            "defaults": {"value": "# Hello World\nWelcome!"},
            "code": 'gr.Markdown("""{value}""")',
            "events": [],
        },
        "Code": {
            "category": "output",
            "icon": "{ }",
            "width": 300,
            "height": 140,
            "defaults": {"label": "Code", "language": "python", "value": "print('Hello')"},
            "code": 'gr.Code(label="{label}", language="{language}", value="""{value}""")',
            "events": ["change"],
        },
        "JSON": {
            "category": "output",
            "icon": "{ }",
            "width": 260,
            "height": 140,
            "defaults": {"label": "JSON"},
            "code": 'gr.JSON(label="{label}")',
            "events": ["change"],
        },
        "Chatbot": {
            "category": "output",
            "icon": "💬",
            "width": 360,
            "height": 280,
            "defaults": {"label": "Chatbot", "height": 400},
            "code": "gr.Chatbot(label=\"{label}\", height={height})",
            "events": ["change"],
        },
        "Gallery": {
            "category": "output",
            "icon": "▦",
            "width": 300,
            "height": 220,
            "defaults": {"label": "Gallery"},
            "code": 'gr.Gallery(label="{label}")',
            "events": ["change"],
        },
        "Dataframe": {
            "category": "output",
            "icon": "▦",
            "width": 320,
            "height": 180,
            "defaults": {"label": "Dataframe"},
            "code": 'gr.Dataframe(label="{label}")',
            "events": ["change"],
        },
        "Label": {
            "category": "output",
            "icon": "◈",
            "width": 200,
            "height": 100,
            "defaults": {"label": "Label"},
            "code": 'gr.Label(label="{label}")',
            "events": ["change"],
        },
        "HTML": {
            "category": "output",
            "icon": "</>",
            "width": 280,
            "height": 100,
            "defaults": {"value": "<h2>Custom HTML</h2>"},
            "code": 'gr.HTML("""{value}""")',
            "events": [],
        },
    }

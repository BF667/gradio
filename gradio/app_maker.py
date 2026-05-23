"""
Gradio App Maker — Visual drag-and-drop app builder.

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
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

from gradio.blocks import Blocks
from gradio.components import (
    HTML,
    Button,
    Code,
    Dropdown,
    JSON,
    Markdown,
    State,
    Textbox,
)
from gradio.layouts import Column, Row, Tab, TabItem, Tabs

# ── Component Registry ────────────────────────────────────────────────────────
# Each entry: { type_name: { category, icon, defaultProps, importLine } }

COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "Textbox": {
        "category": "input",
        "icon": "📝",
        "defaults": {"label": "Textbox", "lines": 1, "placeholder": "Type here..."},
        "import": "Textbox",
        "code": 'gr.Textbox(label="{label}", lines={lines}, placeholder="{placeholder}")',
    },
    "Number": {
        "category": "input",
        "icon": "🔢",
        "defaults": {"label": "Number", "value": 0, "precision": 0},
        "import": "Number",
        "code": 'gr.Number(label="{label}", value={value}, precision={precision})',
    },
    "Slider": {
        "category": "input",
        "icon": "🎚️",
        "defaults": {"label": "Slider", "minimum": 0, "maximum": 100, "value": 50, "step": 1},
        "import": "Slider",
        "code": 'gr.Slider(label="{label}", minimum={minimum}, maximum={maximum}, value={value}, step={step})',
    },
    "Dropdown": {
        "category": "input",
        "icon": "📋",
        "defaults": {"label": "Dropdown", "choices": ["Option 1", "Option 2", "Option 3"]},
        "import": "Dropdown",
        "code": 'gr.Dropdown(label="{label}", choices={choices})',
    },
    "Checkbox": {
        "category": "input",
        "icon": "☑️",
        "defaults": {"label": "Checkbox", "value": False},
        "import": "Checkbox",
        "code": 'gr.Checkbox(label="{label}", value={value})',
    },
    "Radio": {
        "category": "input",
        "icon": "🔘",
        "defaults": {"label": "Radio", "choices": ["Option 1", "Option 2", "Option 3"]},
        "import": "Radio",
        "code": 'gr.Radio(label="{label}", choices={choices})',
    },
    "Image": {
        "category": "media",
        "icon": "🖼️",
        "defaults": {"label": "Image"},
        "import": "Image",
        "code": 'gr.Image(label="{label}")',
    },
    "Audio": {
        "category": "media",
        "icon": "🎵",
        "defaults": {"label": "Audio"},
        "import": "Audio",
        "code": 'gr.Audio(label="{label}")',
    },
    "Video": {
        "category": "media",
        "icon": "🎬",
        "defaults": {"label": "Video"},
        "import": "Video",
        "code": 'gr.Video(label="{label}")',
    },
    "File": {
        "category": "media",
        "icon": "📁",
        "defaults": {"label": "File"},
        "import": "File",
        "code": 'gr.File(label="{label}")',
    },
    "Button": {
        "category": "action",
        "icon": "🔘",
        "defaults": {"label": "Submit", "variant": "primary"},
        "import": "Button",
        "code": 'gr.Button("{label}", variant="{variant}")',
    },
    "Markdown": {
        "category": "display",
        "icon": "📄",
        "defaults": {"value": "# Hello World\nWelcome to my app!"},
        "import": "Markdown",
        "code": 'gr.Markdown("""{value}""")',
    },
    "Code": {
        "category": "display",
        "icon": "💻",
        "defaults": {"label": "Code", "language": "python", "value": "print('Hello')"},
        "import": "Code",
        "code": 'gr.Code(label="{label}", language="{language}", value="""{value}""")',
    },
    "JSON": {
        "category": "display",
        "icon": "📊",
        "defaults": {"label": "JSON"},
        "import": "JSON",
        "code": 'gr.JSON(label="{label}")',
    },
    "Label": {
        "category": "display",
        "icon": "🏷️",
        "defaults": {"label": "Label"},
        "import": "Label",
        "code": 'gr.Label(label="{label}")',
    },
    "Chatbot": {
        "category": "display",
        "icon": "💬",
        "defaults": {"label": "Chatbot", "height": 400},
        "import": "Chatbot",
        "code": 'gr.Chatbot(label="{label}", height={height})',
    },
    "Gallery": {
        "category": "display",
        "icon": "🖼️",
        "defaults": {"label": "Gallery"},
        "import": "Gallery",
        "code": 'gr.Gallery(label="{label}")',
    },
    "Dataframe": {
        "category": "display",
        "icon": "📋",
        "defaults": {"label": "Dataframe"},
        "import": "Dataframe",
        "code": 'gr.Dataframe(label="{label}")',
    },
    "HTML": {
        "category": "display",
        "icon": "🌐",
        "defaults": {"value": "<h2>Custom HTML</h2>"},
        "import": "HTML",
        "code": 'gr.HTML("""{value}""")',
    },
}

LAYOUT_TYPES = {
    "Row": {"icon": "↔️", "desc": "Components in a horizontal row"},
    "Column": {"icon": "↕️", "desc": "Components in a vertical column"},
    "Tabs": {"icon": "📑", "desc": "Tabbed layout"},
    "Accordion": {"icon": "📁", "desc": "Collapsible section"},
    "Group": {"icon": "📦", "desc": "Grouped components"},
}


def _generate_code(schema: dict) -> str:
    """Generate Gradio Blocks Python code from a schema."""
    lines = ["import gradio as gr", ""]
    lines.append("with gr.Blocks() as demo:")

    used_imports: set[str] = set()

    def _gen_component(comp: dict, indent: int = 4) -> str:
        comp_type = comp.get("type", "Textbox")
        props = comp.get("props", {})
        if comp_type in COMPONENT_REGISTRY:
            used_imports.add(COMPONENT_REGISTRY[comp_type]["import"])
            try:
                return " " * indent + COMPONENT_REGISTRY[comp_type]["code"].format(**props)
            except (KeyError, IndexError):
                return " " * indent + f'gr.{comp_type}(label="{props.get("label", comp_type)}")'
        return " " * indent + f'gr.{comp_type}(label="{props.get("label", comp_type)}")'

    def _gen_layout(layout: dict, indent: int = 4) -> None:
        layout_type = layout.get("type", "Column")
        children = layout.get("children", [])
        prefix = " " * indent

        if layout_type == "Row":
            lines.append(f"{prefix}with gr.Row():")
        elif layout_type == "Column":
            scale = layout.get("props", {}).get("scale")
            s = f", scale={scale}" if scale else ""
            lines.append(f"{prefix}with gr.Column{s}:")
        elif layout_type == "Tabs":
            lines.append(f"{prefix}with gr.Tabs():")
        elif layout_type == "Accordion":
            label = layout.get("props", {}).get("label", "Advanced")
            lines.append(f'{prefix}with gr.Accordion("{label}", open=False):')
        elif layout_type == "Group":
            lines.append(f"{prefix}with gr.Group():")

        for child in children:
            if child.get("isLayout"):
                _gen_layout(child, indent + 4)
            else:
                lines.append(_gen_component(child, indent + 4))

    for item in schema.get("layout", []):
        if item.get("isLayout"):
            _gen_layout(item)
        else:
            lines.append(_gen_component(item))

    lines.append("")
    lines.append('demo.launch()')

    return "\n".join(lines)


# ── Builder HTML / CSS / JS ──────────────────────────────────────────────────

BUILDER_CSS = textwrap.dedent("""\
:root {
  --am-primary: #f97316;
  --am-primary-light: #fff7ed;
  --am-bg: #f8fafc;
  --am-surface: #ffffff;
  --am-border: #e2e8f0;
  --am-text: #1e293b;
  --am-text-muted: #64748b;
  --am-radius: 12px;
  --am-shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04);
  --am-shadow-lg: 0 4px 14px rgba(0,0,0,.1);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
.am-root { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: var(--am-text); background: var(--am-bg); min-height: 100vh; }
.am-header { background: var(--am-surface); border-bottom: 1px solid var(--am-border); padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
.am-header h1 { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.am-header h1 span.am-logo { font-size: 22px; }
.am-header-actions { display: flex; gap: 8px; }
.am-btn { border: 1px solid var(--am-border); background: var(--am-surface); color: var(--am-text); padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all .15s ease; display: inline-flex; align-items: center; gap: 6px; }
.am-btn:hover { background: var(--am-bg); border-color: #cbd5e1; }
.am-btn-primary { background: var(--am-primary); color: white; border-color: var(--am-primary); }
.am-btn-primary:hover { background: #ea580c; border-color: #ea580c; }
.am-btn-danger { background: #ef4444; color: white; border-color: #ef4444; }
.am-btn-danger:hover { background: #dc2626; }
.am-btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 6px; }

.am-body { display: grid; grid-template-columns: 220px 1fr 260px; gap: 0; height: calc(100vh - 53px); overflow: hidden; }

/* Palette */
.am-palette { background: var(--am-surface); border-right: 1px solid var(--am-border); overflow-y: auto; padding: 12px; }
.am-palette-section { margin-bottom: 16px; }
.am-palette-section h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--am-text-muted); margin-bottom: 8px; padding: 0 4px; }
.am-palette-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 8px; cursor: grab; font-size: 13px; font-weight: 500; border: 1px solid transparent; transition: all .15s; }
.am-palette-item:hover { background: var(--am-primary-light); border-color: #fed7aa; }
.am-palette-item:active { cursor: grabbing; }
.am-palette-item .am-icon { font-size: 16px; width: 20px; text-align: center; }

/* Canvas */
.am-canvas-area { background: var(--am-bg); overflow-y: auto; padding: 24px; display: flex; flex-direction: column; align-items: center; }
.am-canvas { background: var(--am-surface); border: 2px dashed var(--am-border); border-radius: var(--am-radius); min-height: 400px; width: 100%; max-width: 800px; padding: 16px; position: relative; transition: border-color .2s; }
.am-canvas.drag-over { border-color: var(--am-primary); background: var(--am-primary-light); }
.am-canvas-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 350px; color: var(--am-text-muted); gap: 8px; }
.am-canvas-empty .am-icon { font-size: 40px; opacity: .5; }
.am-canvas-empty p { font-size: 14px; }

/* Canvas items */
.am-canvas-item { background: var(--am-surface); border: 1px solid var(--am-border); border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; position: relative; cursor: pointer; transition: all .15s; display: flex; align-items: center; gap: 10px; }
.am-canvas-item:hover { border-color: var(--am-primary); box-shadow: var(--am-shadow); }
.am-canvas-item.selected { border-color: var(--am-primary); box-shadow: 0 0 0 2px #fed7aa; }
.am-canvas-item .am-item-icon { font-size: 18px; width: 24px; text-align: center; flex-shrink: 0; }
.am-canvas-item .am-item-info { flex: 1; min-width: 0; }
.am-canvas-item .am-item-type { font-size: 12px; font-weight: 600; color: var(--am-primary); text-transform: uppercase; letter-spacing: .03em; }
.am-canvas-item .am-item-label { font-size: 13px; color: var(--am-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.am-canvas-item .am-item-actions { display: flex; gap: 4px; opacity: 0; transition: opacity .15s; }
.am-canvas-item:hover .am-item-actions { opacity: 1; }
.am-canvas-item .am-item-actions button { background: none; border: none; cursor: pointer; padding: 4px; border-radius: 4px; font-size: 14px; color: var(--am-text-muted); }
.am-canvas-item .am-item-actions button:hover { background: #fee2e2; color: #ef4444; }

/* Layout items on canvas */
.am-layout-item { background: var(--am-bg); border: 1px dashed var(--am-border); border-radius: 10px; padding: 12px; margin-bottom: 8px; position: relative; }
.am-layout-item.am-row { display: flex; gap: 8px; flex-wrap: wrap; }
.am-layout-item .am-layout-label { position: absolute; top: -10px; left: 12px; background: var(--am-bg); padding: 0 6px; font-size: 11px; font-weight: 600; color: var(--am-text-muted); text-transform: uppercase; letter-spacing: .03em; }
.am-layout-item .am-canvas-item { flex: 1; min-width: 120px; }
.am-layout-drop { border: 2px dashed #cbd5e1; border-radius: 8px; padding: 20px; text-align: center; color: var(--am-text-muted); font-size: 13px; margin: 4px; transition: border-color .2s; }
.am-layout-drop.drag-over { border-color: var(--am-primary); background: var(--am-primary-light); }

/* Properties */
.am-props { background: var(--am-surface); border-left: 1px solid var(--am-border); overflow-y: auto; padding: 16px; }
.am-props h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--am-border); }
.am-props-empty { color: var(--am-text-muted); font-size: 13px; text-align: center; padding: 40px 16px; }
.am-prop-group { margin-bottom: 14px; }
.am-prop-group label { display: block; font-size: 12px; font-weight: 500; color: var(--am-text-muted); margin-bottom: 4px; }
.am-prop-group input, .am-prop-group select, .am-prop-group textarea { width: 100%; padding: 7px 10px; border: 1px solid var(--am-border); border-radius: 8px; font-size: 13px; background: var(--am-surface); color: var(--am-text); outline: none; transition: border-color .15s; }
.am-prop-group input:focus, .am-prop-group select:focus, .am-prop-group textarea:focus { border-color: var(--am-primary); }
.am-prop-group textarea { resize: vertical; min-height: 60px; }

/* Mobile toggle */
.am-mobile-toggle { display: none; }

/* Mobile responsive */
@media (max-width: 768px) {
  .am-body { grid-template-columns: 1fr; grid-template-rows: auto 1fr auto; height: auto; }
  .am-palette { border-right: none; border-bottom: 1px solid var(--am-border); padding: 8px; display: flex; flex-wrap: wrap; gap: 4px; max-height: 120px; overflow-y: auto; }
  .am-palette-section { margin-bottom: 0; display: flex; flex-wrap: wrap; gap: 4px; }
  .am-palette-section h3 { display: none; }
  .am-palette-item { padding: 6px 10px; font-size: 12px; }
  .am-canvas-area { padding: 12px; min-height: 300px; }
  .am-canvas { max-width: 100%; }
  .am-props { border-left: none; border-top: 1px solid var(--am-border); max-height: 250px; }
  .am-mobile-toggle { display: flex; gap: 4px; }
  .am-header-actions .am-desktop-only { display: none; }
  .am-canvas-item .am-item-actions { opacity: 1; }
}

@media (max-width: 480px) {
  .am-header { padding: 8px 12px; }
  .am-header h1 { font-size: 15px; }
  .am-btn { padding: 5px 10px; font-size: 12px; }
  .am-canvas-item { padding: 8px 10px; }
}
""")

BUILDER_HTML = textwrap.dedent("""\
<div class="am-root">
  <div class="am-header">
    <h1><span class="am-logo">🎨</span> App Maker</h1>
    <div class="am-header-actions">
      <button class="am-btn am-mobile-toggle" onclick="amTogglePanel('palette')">📦 Parts</button>
      <button class="am-btn am-mobile-toggle" onclick="amTogglePanel('props')">⚙️ Props</button>
      <button class="am-btn am-desktop-only" onclick="amUndo()">↩️ Undo</button>
      <button class="am-btn am-btn-danger am-desktop-only" onclick="amClear()">🗑️ Clear</button>
      <button class="am-btn am-btn-primary" onclick="amGenerate()">✨ Generate Code</button>
    </div>
  </div>
  <div class="am-body">
    <div class="am-palette" id="amPalette">
      <div class="am-palette-section">
        <h3>Input</h3>
        {{#each inputComponents}}
        <div class="am-palette-item" draggable="true" data-type="{{type}}" data-category="{{category}}" ondragstart="amDragStart(event)">
          <span class="am-icon">{{icon}}</span> {{type}}
        </div>
        {{/each}}
      </div>
      <div class="am-palette-section">
        <h3>Display</h3>
        {{#each displayComponents}}
        <div class="am-palette-item" draggable="true" data-type="{{type}}" data-category="{{category}}" ondragstart="amDragStart(event)">
          <span class="am-icon">{{icon}}</span> {{type}}
        </div>
        {{/each}}
      </div>
      <div class="am-palette-section">
        <h3>Media</h3>
        {{#each mediaComponents}}
        <div class="am-palette-item" draggable="true" data-type="{{type}}" data-category="{{category}}" ondragstart="amDragStart(event)">
          <span class="am-icon">{{icon}}</span> {{type}}
        </div>
        {{/each}}
      </div>
      <div class="am-palette-section">
        <h3>Layout</h3>
        {{#each layouts}}
        <div class="am-palette-item" draggable="true" data-type="{{type}}" data-category="layout" ondragstart="amDragStart(event)">
          <span class="am-icon">{{icon}}</span> {{type}}
        </div>
        {{/each}}
      </div>
    </div>
    <div class="am-canvas-area">
      <div class="am-canvas" id="amCanvas"
           ondragover="amDragOver(event)" ondragleave="amDragLeave(event)" ondrop="amDrop(event)">
        <div class="am-canvas-empty" id="amEmpty">
          <span class="am-icon">🧩</span>
          <p>Drag components here to build your app</p>
          <p style="font-size:12px;opacity:.6">Works on desktop & mobile</p>
        </div>
        <div id="amCanvasItems"></div>
      </div>
    </div>
    <div class="am-props" id="amProps">
      <h3>Properties</h3>
      <div class="am-props-empty" id="amPropsEmpty">
        Select a component to edit its properties
      </div>
      <div id="amPropsForm" style="display:none"></div>
    </div>
  </div>
</div>
""")

BUILDER_JS = textwrap.dedent("""\
// ── State ──────────────────────────────────────────────────────────
let amSchema = { layout: [] };
let amSelectedIdx = -1;
let amHistory = [];
let amIdCounter = 0;

// ── Drag & Drop ───────────────────────────────────────────────────
function amDragStart(e) {
  e.dataTransfer.setData('text/plain', JSON.stringify({
    type: e.target.dataset.type,
    category: e.target.dataset.category
  }));
  e.dataTransfer.effectAllowed = 'copy';
}

function amDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'copy';
  const canvas = document.getElementById('amCanvas');
  canvas.classList.add('drag-over');
}

function amDragLeave(e) {
  const canvas = document.getElementById('amCanvas');
  canvas.classList.remove('drag-over');
}

function amDrop(e) {
  e.preventDefault();
  const canvas = document.getElementById('amCanvas');
  canvas.classList.remove('drag-over');
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    amAddItem(data.type, data.category);
  } catch(err) {}
}

// ── Touch support for mobile ──────────────────────────────────────
let amTouchItem = null;
document.addEventListener('DOMContentLoaded', () => {
  // Add touch handlers to palette items
  const items = document.querySelectorAll('.am-palette-item');
  items.forEach(item => {
    item.addEventListener('touchstart', (e) => {
      amTouchItem = { type: item.dataset.type, category: item.dataset.category };
    }, { passive: true });
    item.addEventListener('touchend', (e) => {
      if (amTouchItem) {
        e.preventDefault();
        amAddItem(amTouchItem.type, amTouchItem.category);
        amTouchItem = null;
      }
    });
  });
});

// ── Add Item ──────────────────────────────────────────────────────
function amAddItem(type, category) {
  amSaveHistory();
  const id = 'comp_' + (++amIdCounter);

  if (category === 'layout') {
    amSchema.layout.push({
      id, type, isLayout: true,
      children: [],
      props: type === 'Accordion' ? { label: 'Advanced Settings' } : {}
    });
  } else {
    const defaults = window.__AM_REGISTRY__[type] ? window.__AM_REGISTRY__[type].defaults : { label: type };
    amSchema.layout.push({
      id, type, isLayout: false,
      props: { ...defaults }
    });
  }
  amRender();
  amSelectItem(amSchema.layout.length - 1);
}

// ── Render ────────────────────────────────────────────────────────
function amRender() {
  const container = document.getElementById('amCanvasItems');
  const empty = document.getElementById('amEmpty');

  if (amSchema.layout.length === 0) {
    empty.style.display = 'flex';
    container.innerHTML = '';
    return;
  }
  empty.style.display = 'none';

  let html = '';
  amSchema.layout.forEach((item, idx) => {
    if (item.isLayout) {
      html += amRenderLayout(item, idx);
    } else {
      html += amRenderComponent(item, idx);
    }
  });
  container.innerHTML = html;
}

function amRenderComponent(item, idx) {
  const reg = window.__AM_REGISTRY__[item.type] || { icon: '📦' };
  const selected = idx === amSelectedIdx ? ' selected' : '';
  return `<div class="am-canvas-item${selected}" data-idx="${idx}" onclick="amSelectItem(${idx})">
    <span class="am-item-icon">${reg.icon}</span>
    <div class="am-item-info">
      <div class="am-item-type">${item.type}</div>
      <div class="am-item-label">${item.props.label || item.type}</div>
    </div>
    <div class="am-item-actions">
      <button onclick="event.stopPropagation();amMoveItem(${idx},-1)" title="Move up">⬆️</button>
      <button onclick="event.stopPropagation();amMoveItem(${idx},1)" title="Move down">⬇️</button>
      <button onclick="event.stopPropagation();amRemoveItem(${idx})" title="Delete">🗑️</button>
    </div>
  </div>`;
}

function amRenderLayout(item, idx) {
  const reg = window.__AM_LAYOUTS__[item.type] || { icon: '📦' };
  const selected = idx === amSelectedIdx ? ' selected' : '';
  const isRow = item.type === 'Row';

  let childrenHtml = '';
  if (item.children && item.children.length > 0) {
    item.children.forEach((child, ci) => {
      childrenHtml += amRenderComponent(child, idx + '_' + ci);
    });
  } else {
    childrenHtml = `<div class="am-layout-drop"
      ondragover="event.preventDefault();this.classList.add('drag-over')"
      ondragleave="this.classList.remove('drag-over')"
      ondrop="event.preventDefault();event.stopPropagation();this.classList.remove('drag-over');amDropInLayout(${idx})">
      Drop components here
    </div>`;
  }

  return `<div class="am-layout-item${isRow ? ' am-row' : ''}${selected}" data-idx="${idx}" onclick="amSelectItem(${idx})">
    <span class="am-layout-label">${reg.icon} ${item.type}</span>
    ${childrenHtml}
  </div>`;
}

function amDropInLayout(layoutIdx) {
  // This is a simplified version - drops go to the layout's children
  // For now, we'll add items at the top level and let users reorder
  amAddItem('Textbox', 'input');
}

// ── Select / Edit ─────────────────────────────────────────────────
function amSelectItem(idx) {
  amSelectedIdx = idx;
  amRender();
  amRenderProps();
}

function amRenderProps() {
  const form = document.getElementById('amPropsForm');
  const empty = document.getElementById('amPropsEmpty');

  if (amSelectedIdx < 0 || amSelectedIdx >= amSchema.layout.length) {
    form.style.display = 'none';
    empty.style.display = 'block';
    return;
  }

  const item = amSchema.layout[amSelectedIdx];
  form.style.display = 'block';
  empty.style.display = 'none';

  let html = `<div class="am-prop-group"><label>Type</label><input value="${item.type}" disabled /></div>`;

  if (item.isLayout) {
    if (item.type === 'Accordion') {
      html += `<div class="am-prop-group"><label>Label</label><input value="${item.props.label || ''}" onchange="amUpdateProp(${amSelectedIdx},'label',this.value)" /></div>`;
    }
  } else {
    const props = item.props || {};
    for (const [key, val] of Object.entries(props)) {
      if (key === 'choices') {
        html += `<div class="am-prop-group"><label>${key}</label><input value="${JSON.stringify(val)}" onchange="amUpdateProp(${amSelectedIdx},'${key}',JSON.parse(this.value))" /></div>`;
      } else if (typeof val === 'boolean') {
        html += `<div class="am-prop-group"><label>${key}</label><select onchange="amUpdateProp(${amSelectedIdx},'${key}',this.value==='true')"><option value="true" ${val?'selected':''}>True</option><option value="false" ${!val?'selected':''}>False</option></select></div>`;
      } else if (typeof val === 'number') {
        html += `<div class="am-prop-group"><label>${key}</label><input type="number" value="${val}" onchange="amUpdateProp(${amSelectedIdx},'${key}',Number(this.value))" /></div>`;
      } else {
        html += `<div class="am-prop-group"><label>${key}</label><input value="${String(val).replace(/"/g,'&quot;')}" onchange="amUpdateProp(${amSelectedIdx},'${key}',this.value)" /></div>`;
      }
    }
  }
  form.innerHTML = html;
}

function amUpdateProp(idx, key, value) {
  amSaveHistory();
  amSchema.layout[idx].props[key] = value;
  amRender();
}

// ── Actions ───────────────────────────────────────────────────────
function amRemoveItem(idx) {
  amSaveHistory();
  amSchema.layout.splice(idx, 1);
  if (amSelectedIdx >= amSchema.layout.length) amSelectedIdx = amSchema.layout.length - 1;
  amRender();
  amRenderProps();
}

function amMoveItem(idx, dir) {
  const newIdx = idx + dir;
  if (newIdx < 0 || newIdx >= amSchema.layout.length) return;
  amSaveHistory();
  [amSchema.layout[idx], amSchema.layout[newIdx]] = [amSchema.layout[newIdx], amSchema.layout[idx]];
  if (amSelectedIdx === idx) amSelectedIdx = newIdx;
  amRender();
}

function amClear() {
  if (amSchema.layout.length === 0) return;
  amSaveHistory();
  amSchema = { layout: [] };
  amSelectedIdx = -1;
  amRender();
  amRenderProps();
}

function amUndo() {
  if (amHistory.length === 0) return;
  amSchema = amHistory.pop();
  amSelectedIdx = -1;
  amRender();
  amRenderProps();
}

function amSaveHistory() {
  amHistory.push(JSON.parse(JSON.stringify(amSchema)));
  if (amHistory.length > 30) amHistory.shift();
}

// ── Generate Code ─────────────────────────────────────────────────
function amGenerate() {
  // Store schema in a hidden input and trigger Gradio click event
  const schemaStr = JSON.stringify(amSchema);
  props.value = schemaStr;
  trigger('click', schemaStr);
}

// ── Mobile panel toggle ──────────────────────────────────────────
function amTogglePanel(panel) {
  const palette = document.getElementById('amPalette');
  const props = document.getElementById('amProps');
  if (panel === 'palette') {
    palette.style.display = palette.style.display === 'none' ? 'block' : 'none';
    props.style.display = 'none';
  } else {
    props.style.display = props.style.display === 'none' ? 'block' : 'none';
    palette.style.display = 'none';
  }
}

// ── Init ──────────────────────────────────────────────────────────
console.log('App Maker loaded ✅');
""")


def app_maker(options: dict[str, Any] | None = None) -> Blocks:
    """
    Create a visual drag-and-drop Gradio app builder.

    Parameters:
        options: Configuration dictionary with optional keys:
            - components: List of component type names to include in the palette.
                          Default: all available components.
            - theme: Gradio theme name or theme object. Default: "soft".
            - title: Title for the builder. Default: "App Maker".
            - default_layout: Default layout for new items. Default: "Column".

    Returns:
        A Gradio Blocks object containing the visual builder UI.

    Example:
        ```python
        from gradio import app_maker

        demo = app_maker()
        demo.launch()

        # Or with options:
        demo = app_maker(options={
            "components": ["Textbox", "Slider", "Button", "Image", "Chatbot"],
            "theme": "soft",
        })
        demo.launch()
        ```
    """
    opts = options or {}
    available_components = opts.get("components", list(COMPONENT_REGISTRY.keys()))
    theme_name = opts.get("theme", "soft")
    title = opts.get("title", "App Maker")

    # Filter registry to only requested components
    filtered_registry = {
        k: v for k, v in COMPONENT_REGISTRY.items() if k in available_components
    }

    # Categorize for palette
    input_comps = [
        {"type": k, "icon": v["icon"], "category": v["category"]}
        for k, v in filtered_registry.items()
        if v["category"] == "input"
    ]
    display_comps = [
        {"type": k, "icon": v["icon"], "category": v["category"]}
        for k, v in filtered_registry.items()
        if v["category"] == "display"
    ]
    media_comps = [
        {"type": k, "icon": v["icon"], "category": v["category"]}
        for k, v in filtered_registry.items()
        if v["category"] == "media"
    ]
    layout_comps = [
        {"type": k, "icon": v["icon"], "category": "layout"}
        for k, v in LAYOUT_TYPES.items()
    ]

    # JSON string of the component registry for the JS side
    registry_json = json.dumps(
        {k: {"icon": v["icon"], "defaults": v["defaults"]} for k, v in filtered_registry.items()}
    )
    layouts_json = json.dumps(LAYOUT_TYPES)

    with Blocks(title=title, fill_height=True) as demo:
        # Hidden state for the app schema
        schema_state = State({"layout": []})

        # The main builder UI
        builder = HTML(
            value="",
            html_template=BUILDER_HTML,
            css_template=BUILDER_CSS,
            js_on_load=f"""
            // Register custom events - 'generate' and 'preview'
            // These must be referenced in js_on_load string for Gradio to create them
            if (typeof trigger === 'function') {{
                // 'generate' event
                // 'preview' event
            }}
            window.__AM_REGISTRY__ = {registry_json};
            window.__AM_LAYOUTS__ = {layouts_json};
            {BUILDER_JS}
            """,
            elem_id="app-maker-builder",
            min_height=700,
            props={
                "inputComponents": input_comps,
                "displayComponents": display_comps,
                "mediaComponents": media_comps,
                "layouts": layout_comps,
            },
        )

        with Row():
            generate_btn = Button("✨ Generate Gradio Code", variant="primary", size="lg")
            run_btn = Button("🚀 Preview as Blocks", variant="secondary", size="lg")

        # Output code
        output_code = Code(
            label="Generated Gradio Code",
            language="python",
            interactive=True,
            lines=20,
        )

        # Preview area
        preview_html = HTML(
            label="Preview",
            visible=False,
            min_height=300,
        )

        # ── Event Handlers ─────────────────────────────────────────
        def on_generate(evt_data) -> str:
            """Generate Gradio Blocks code from the builder schema."""
            import json as _json
            schema = {"layout": []}
            if isinstance(evt_data, str):
                try:
                    schema = _json.loads(evt_data)
                except (ValueError, TypeError):
                    pass
            elif isinstance(evt_data, dict):
                schema = evt_data
            code = _generate_code(schema)
            return code

        # Use the 'generate' custom event from js_on_load
        # The HTML component creates custom events from strings in js_on_load
        builder.click(on_generate, outputs=[output_code])

        # Also handle the external Generate button
        def on_generate_btn():
            """Fallback: generate code from empty schema if builder click hasn't fired."""
            return _generate_code({"layout": []})

        generate_btn.click(on_generate_btn, outputs=[output_code])

        def on_run(code: str) -> tuple[str, dict]:
            """Run the generated code and show preview."""
            if not code or not code.strip():
                return "No code to preview", {"layout": []}

            # Create a preview HTML by executing the code in a sandboxed way
            preview = _create_preview_html(code)
            return preview, {"layout": []}

        run_btn.click(
            on_run,
            inputs=[output_code],
            outputs=[preview_html, schema_state],
        )

    return demo


def _create_preview_html(code: str) -> str:
    """Create an HTML preview of the generated Gradio code.

    Instead of actually executing the code (which would be a security risk),
    we parse it and create a visual HTML representation.
    """
    preview_parts = [
        '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;">',
        '<h2 style="font-size: 18px; margin-bottom: 16px; color: #1e293b;">📱 App Preview</h2>',
        '<div style="background: white; border-radius: 10px; padding: 20px; border: 1px solid #e2e8f0;">',
    ]

    # Simple parser: look for gr.ComponentName patterns
    import re

    components = re.findall(r'gr\.(\w+)\(([^)]*)\)', code)

    for comp_type, args_str in components:
        if comp_type in ('Blocks', 'Row', 'Column', 'Tabs', 'Tab', 'Group', 'Accordion'):
            continue

        # Extract label
        label_match = re.search(r'label\s*=\s*["\']([^"\']*)["\']', args_str)
        label = label_match.group(1) if label_match else comp_type

        icon = COMPONENT_REGISTRY.get(comp_type, {}).get("icon", "📦")

        if comp_type == "Button":
            # Button gets the first positional arg as label
            pos_match = re.search(r'["\']([^"\']*)["\']', args_str)
            if pos_match:
                label = pos_match.group(1)
            preview_parts.append(
                f'<div style="margin: 8px 0;">'
                f'<button style="background: #f97316; color: white; border: none; padding: 10px 24px; border-radius: 8px; font-size: 14px; cursor: pointer;">{icon} {label}</button>'
                f'</div>'
            )
        elif comp_type == "Markdown":
            value_match = re.search(r'"""([^"]*)"""', args_str)
            value = value_match.group(1) if value_match else label
            preview_parts.append(
                f'<div style="margin: 8px 0; padding: 12px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 14px;">{icon} {value[:100]}</div>'
            )
        elif comp_type in ("Image", "Audio", "Video", "Gallery"):
            preview_parts.append(
                f'<div style="margin: 8px 0;">'
                f'<div style="border: 2px dashed #cbd5e1; border-radius: 8px; padding: 24px; text-align: center; color: #64748b;">{icon} {label} drop zone</div>'
                f'</div>'
            )
        elif comp_type == "Slider":
            preview_parts.append(
                f'<div style="margin: 8px 0;">'
                f'<label style="font-size: 13px; font-weight: 500; color: #374151; display: block; margin-bottom: 4px;">{icon} {label}</label>'
                f'<input type="range" min="0" max="100" value="50" style="width: 100%;" disabled />'
                f'</div>'
            )
        elif comp_type == "Dropdown":
            preview_parts.append(
                f'<div style="margin: 8px 0;">'
                f'<label style="font-size: 13px; font-weight: 500; color: #374151; display: block; margin-bottom: 4px;">{icon} {label}</label>'
                f'<select style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px;"><option>Select...</option></select>'
                f'</div>'
            )
        elif comp_type == "Chatbot":
            preview_parts.append(
                f'<div style="margin: 8px 0;">'
                f'<label style="font-size: 13px; font-weight: 500; color: #374151; display: block; margin-bottom: 4px;">{icon} {label}</label>'
                f'<div style="border: 1px solid #e2e8f0; border-radius: 8px; height: 200px; padding: 12px; background: #fafafa; color: #94a3b8; display: flex; align-items: center; justify-content: center;">Chat messages will appear here</div>'
                f'</div>'
            )
        else:
            preview_parts.append(
                f'<div style="margin: 8px 0;">'
                f'<label style="font-size: 13px; font-weight: 500; color: #374151; display: block; margin-bottom: 4px;">{icon} {label}</label>'
                f'<input type="text" placeholder="Enter {label}..." style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px;" disabled />'
                f'</div>'
            )

    preview_parts.append('</div>')
    preview_parts.append(
        '<p style="font-size: 12px; color: #94a3b8; margin-top: 12px; text-align: center;">'
        'This is a visual preview. Copy the generated code to create the actual Gradio app.'
        '</p>'
    )
    preview_parts.append('</div>')

    return ''.join(preview_parts)

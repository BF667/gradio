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
import textwrap
from typing import Any

from gradio.blocks import Blocks
from gradio.components import (
    HTML,
    Button,
    Code,
    State,
)
from gradio.layouts import Row

# ── Component Registry ────────────────────────────────────────────────────────

COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "Textbox": {
        "category": "input",
        "icon": "📝",
        "width": 220,
        "height": 80,
        "defaults": {"label": "Textbox", "lines": 1, "placeholder": "Type here..."},
        "code": 'gr.Textbox(label="{label}", lines={lines}, placeholder="{placeholder}")',
    },
    "Number": {
        "category": "input",
        "icon": "🔢",
        "width": 180,
        "height": 70,
        "defaults": {"label": "Number", "value": 0, "precision": 0},
        "code": 'gr.Number(label="{label}", value={value}, precision={precision})',
    },
    "Slider": {
        "category": "input",
        "icon": "🎚️",
        "width": 240,
        "height": 70,
        "defaults": {"label": "Slider", "minimum": 0, "maximum": 100, "value": 50, "step": 1},
        "code": 'gr.Slider(label="{label}", minimum={minimum}, maximum={maximum}, value={value}, step={step})',
    },
    "Dropdown": {
        "category": "input",
        "icon": "📋",
        "width": 220,
        "height": 70,
        "defaults": {"label": "Dropdown", "choices": ["Option 1", "Option 2", "Option 3"]},
        "code": 'gr.Dropdown(label="{label}", choices={choices})',
    },
    "Checkbox": {
        "category": "input",
        "icon": "☑️",
        "width": 180,
        "height": 60,
        "defaults": {"label": "Checkbox", "value": False},
        "code": 'gr.Checkbox(label="{label}", value={value})',
    },
    "Radio": {
        "category": "input",
        "icon": "🔘",
        "width": 220,
        "height": 90,
        "defaults": {"label": "Radio", "choices": ["Option 1", "Option 2", "Option 3"]},
        "code": 'gr.Radio(label="{label}", choices={choices})',
    },
    "Image": {
        "category": "media",
        "icon": "🖼️",
        "width": 220,
        "height": 180,
        "defaults": {"label": "Image"},
        "code": 'gr.Image(label="{label}")',
    },
    "Audio": {
        "category": "media",
        "icon": "🎵",
        "width": 220,
        "height": 120,
        "defaults": {"label": "Audio"},
        "code": 'gr.Audio(label="{label}")',
    },
    "Video": {
        "category": "media",
        "icon": "🎬",
        "width": 280,
        "height": 200,
        "defaults": {"label": "Video"},
        "code": 'gr.Video(label="{label}")',
    },
    "File": {
        "category": "media",
        "icon": "📁",
        "width": 220,
        "height": 80,
        "defaults": {"label": "File"},
        "code": 'gr.File(label="{label}")',
    },
    "Button": {
        "category": "action",
        "icon": "🔴",
        "width": 160,
        "height": 56,
        "defaults": {"label": "Submit", "variant": "primary"},
        "code": 'gr.Button("{label}", variant="{variant}")',
    },
    "Markdown": {
        "category": "display",
        "icon": "📄",
        "width": 300,
        "height": 100,
        "defaults": {"value": "# Hello World\nWelcome!"},
        "code": 'gr.Markdown("""{value}""")',
    },
    "Code": {
        "category": "display",
        "icon": "💻",
        "width": 300,
        "height": 140,
        "defaults": {"label": "Code", "language": "python", "value": "print('Hello')"},
        "code": 'gr.Code(label="{label}", language="{language}", value="""{value}""")',
    },
    "JSON": {
        "category": "display",
        "icon": "📊",
        "width": 260,
        "height": 140,
        "defaults": {"label": "JSON"},
        "code": 'gr.JSON(label="{label}")',
    },
    "Label": {
        "category": "display",
        "icon": "🏷️",
        "width": 200,
        "height": 100,
        "defaults": {"label": "Label"},
        "code": 'gr.Label(label="{label}")',
    },
    "Chatbot": {
        "category": "display",
        "icon": "💬",
        "width": 360,
        "height": 280,
        "defaults": {"label": "Chatbot", "height": 400},
        "code": 'gr.Chatbot(label="{label}", height={height})',
    },
    "Gallery": {
        "category": "display",
        "icon": "🖼️",
        "width": 300,
        "height": 220,
        "defaults": {"label": "Gallery"},
        "code": 'gr.Gallery(label="{label}")',
    },
    "Dataframe": {
        "category": "display",
        "icon": "📋",
        "width": 320,
        "height": 180,
        "defaults": {"label": "Dataframe"},
        "code": 'gr.Dataframe(label="{label}")',
    },
    "HTML": {
        "category": "display",
        "icon": "🌐",
        "width": 280,
        "height": 100,
        "defaults": {"value": "<h2>Custom HTML</h2>"},
        "code": 'gr.HTML("""{value}""")',
    },
}


def _generate_code(schema: dict) -> str:
    """Generate Gradio Blocks Python code from a schema."""
    lines = ["import gradio as gr", ""]
    lines.append("with gr.Blocks() as demo:")

    items = schema.get("layout", [])
    # Sort by y then x for code order (top-to-bottom, left-to-right)
    sorted_items = sorted(items, key=lambda c: (c.get("y", 0), c.get("x", 0)))

    for item in sorted_items:
        comp_type = item.get("type", "Textbox")
        props = item.get("props", {})
        if comp_type in COMPONENT_REGISTRY:
            try:
                lines.append("    " + COMPONENT_REGISTRY[comp_type]["code"].format(**props))
            except (KeyError, IndexError):
                lines.append(f'    gr.{comp_type}(label="{props.get("label", comp_type)}")')
        else:
            lines.append(f'    gr.{comp_type}(label="{props.get("label", comp_type)}")')

    lines.append("")
    lines.append("demo.launch()")
    return "\n".join(lines)


# ── Builder HTML / CSS / JS ──────────────────────────────────────────────────

BUILDER_CSS = textwrap.dedent("""\
:root {
  --am-primary: #f97316;
  --am-primary-light: #fff7ed;
  --am-bg: #f1f5f9;
  --am-surface: #ffffff;
  --am-border: #e2e8f0;
  --am-text: #1e293b;
  --am-text-muted: #64748b;
  --am-radius: 12px;
  --am-shadow: 0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06);
  --am-shadow-lg: 0 8px 24px rgba(0,0,0,.12);
  --am-grid: 20px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
.am-root { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: var(--am-text); background: var(--am-bg); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

/* Header */
.am-header { background: var(--am-surface); border-bottom: 1px solid var(--am-border); padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; z-index: 100; flex-shrink: 0; }
.am-header h1 { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
.am-header-actions { display: flex; gap: 6px; align-items: center; }
.am-btn { border: 1px solid var(--am-border); background: var(--am-surface); color: var(--am-text); padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all .15s; display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
.am-btn:hover { background: var(--am-bg); border-color: #cbd5e1; }
.am-btn-primary { background: var(--am-primary); color: white; border-color: var(--am-primary); }
.am-btn-primary:hover { background: #ea580c; }
.am-btn-danger { color: #ef4444; }
.am-btn-danger:hover { background: #fef2f2; }

/* Main layout */
.am-body { display: flex; flex: 1; overflow: hidden; }

/* Sidebar */
.am-sidebar { width: 200px; background: var(--am-surface); border-right: 1px solid var(--am-border); overflow-y: auto; padding: 10px; flex-shrink: 0; }
.am-sidebar h3 { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--am-text-muted); margin-bottom: 6px; margin-top: 10px; padding: 0 4px; }
.am-sidebar h3:first-child { margin-top: 0; }
.am-sidebar-item { display: flex; align-items: center; gap: 7px; padding: 7px 9px; border-radius: 7px; cursor: pointer; font-size: 12px; font-weight: 500; border: 1px solid transparent; transition: all .12s; user-select: none; }
.am-sidebar-item:hover { background: var(--am-primary-light); border-color: #fed7aa; }
.am-sidebar-item:active { transform: scale(.97); }
.am-sidebar-item .am-icon { font-size: 14px; width: 18px; text-align: center; }

/* Canvas area */
.am-canvas-wrap { flex: 1; overflow: auto; position: relative; background: var(--am-bg); }
.am-canvas { position: relative; width: 2000px; height: 2000px; background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1px); background-size: var(--am-grid) var(--am-grid); }

/* Free-form widget on canvas */
.am-widget { position: absolute; background: var(--am-surface); border: 2px solid var(--am-border); border-radius: 10px; cursor: move; user-select: none; transition: box-shadow .15s, border-color .15s; overflow: hidden; }
.am-widget:hover { border-color: #fdba74; box-shadow: var(--am-shadow); z-index: 10; }
.am-widget.selected { border-color: var(--am-primary); box-shadow: 0 0 0 3px rgba(249,115,22,.2); z-index: 20; }
.am-widget-header { display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: #f8fafc; border-bottom: 1px solid var(--am-border); font-size: 11px; font-weight: 600; color: var(--am-text-muted); text-transform: uppercase; letter-spacing: .03em; cursor: move; }
.am-widget-header .am-icon { font-size: 13px; }
.am-widget-body { padding: 10px 12px; font-size: 13px; color: var(--am-text); overflow: hidden; }
.am-widget-body input[type=text] { width: 100%; padding: 5px 8px; border: 1px solid var(--am-border); border-radius: 5px; font-size: 12px; pointer-events: none; }
.am-widget-body input[type=range] { width: 100%; pointer-events: none; }
.am-widget-body select { width: 100%; padding: 5px; border: 1px solid var(--am-border); border-radius: 5px; font-size: 12px; pointer-events: none; }
.am-widget-body .am-placeholder { color: var(--am-text-muted); font-size: 12px; font-style: italic; }
.am-widget-body button { padding: 6px 16px; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: default; }
.am-widget-body .am-btn-primary-prev { background: var(--am-primary); color: white; }

/* Widget delete handle */
.am-widget-del { position: absolute; top: 4px; right: 4px; width: 20px; height: 20px; border-radius: 50%; background: #ef4444; color: white; border: none; font-size: 11px; cursor: pointer; display: none; align-items: center; justify-content: center; z-index: 30; line-height: 1; }
.am-widget:hover .am-widget-del { display: flex; }

/* Resize handle */
.am-widget-resize { position: absolute; bottom: 0; right: 0; width: 16px; height: 16px; cursor: nwse-resize; opacity: 0; }
.am-widget:hover .am-widget-resize, .am-widget.selected .am-widget-resize { opacity: 1; }
.am-widget-resize::after { content: ''; position: absolute; bottom: 3px; right: 3px; width: 8px; height: 8px; border-right: 2px solid var(--am-primary); border-bottom: 2px solid var(--am-primary); }

/* Add button floating on canvas */
.am-add-fab { position: absolute; bottom: 20px; right: 20px; width: 52px; height: 52px; border-radius: 50%; background: var(--am-primary); color: white; border: none; font-size: 26px; cursor: pointer; box-shadow: 0 4px 14px rgba(249,115,22,.4); z-index: 50; display: flex; align-items: center; justify-content: center; transition: transform .15s, box-shadow .15s; }
.am-add-fab:hover { transform: scale(1.1); box-shadow: 0 6px 20px rgba(249,115,22,.5); }

/* Add menu popup */
.am-add-menu { position: absolute; bottom: 80px; right: 20px; background: var(--am-surface); border: 1px solid var(--am-border); border-radius: 12px; box-shadow: var(--am-shadow-lg); padding: 10px; z-index: 60; width: 220px; max-height: 400px; overflow-y: auto; display: none; }
.am-add-menu.open { display: block; }
.am-add-menu h4 { font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: var(--am-text-muted); margin: 6px 0 4px; padding: 0 4px; }
.am-add-menu-item { display: flex; align-items: center; gap: 7px; padding: 7px 9px; border-radius: 7px; cursor: pointer; font-size: 12px; font-weight: 500; transition: background .1s; }
.am-add-menu-item:hover { background: var(--am-primary-light); }

/* Props panel */
.am-props { width: 240px; background: var(--am-surface); border-left: 1px solid var(--am-border); overflow-y: auto; padding: 14px; flex-shrink: 0; }
.am-props h3 { font-size: 13px; font-weight: 600; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--am-border); }
.am-props-empty { color: var(--am-text-muted); font-size: 12px; text-align: center; padding: 30px 10px; }
.am-prop-group { margin-bottom: 10px; }
.am-prop-group label { display: block; font-size: 11px; font-weight: 500; color: var(--am-text-muted); margin-bottom: 3px; }
.am-prop-group input, .am-prop-group select, .am-prop-group textarea { width: 100%; padding: 5px 8px; border: 1px solid var(--am-border); border-radius: 6px; font-size: 12px; background: var(--am-surface); color: var(--am-text); outline: none; transition: border-color .12s; }
.am-prop-group input:focus, .am-prop-group select:focus { border-color: var(--am-primary); }
.am-prop-row { display: flex; gap: 6px; }
.am-prop-row .am-prop-group { flex: 1; }

/* Mobile toggle */
.am-mobile-toggle { display: none; }

/* Mobile responsive */
@media (max-width: 900px) {
  .am-sidebar { width: 160px; }
  .am-props { width: 200px; }
}

@media (max-width: 768px) {
  .am-body { flex-direction: column; }
  .am-sidebar { width: 100%; max-height: 80px; border-right: none; border-bottom: 1px solid var(--am-border); display: flex; flex-wrap: wrap; gap: 2px; padding: 6px; overflow-x: auto; overflow-y: hidden; }
  .am-sidebar h3 { display: none; }
  .am-sidebar-item { padding: 5px 8px; font-size: 11px; }
  .am-canvas-wrap { flex: 1; min-height: 300px; }
  .am-props { width: 100%; max-height: 200px; border-left: none; border-top: 1px solid var(--am-border); }
  .am-mobile-toggle { display: inline-flex; }
  .am-desktop-only { display: none !important; }
}

@media (max-width: 480px) {
  .am-header { padding: 6px 10px; }
  .am-header h1 { font-size: 14px; }
  .am-btn { padding: 4px 8px; font-size: 11px; }
  .am-sidebar-item { padding: 4px 6px; font-size: 10px; }
}
""")

BUILDER_HTML = textwrap.dedent("""\
<div class="am-root">
  <div class="am-header">
    <h1><span>🎨</span> App Maker</h1>
    <div class="am-header-actions">
      <button class="am-btn am-mobile-toggle" onclick="amTogglePanel('sidebar')">📦</button>
      <button class="am-btn am-mobile-toggle" onclick="amTogglePanel('props')">⚙️</button>
      <button class="am-btn am-desktop-only" onclick="amUndo()">↩️ Undo</button>
      <button class="am-btn am-btn-danger am-desktop-only" onclick="amClear()">🗑️ Clear</button>
      <button class="am-btn am-btn-primary" onclick="amGenerate()">✨ Generate</button>
    </div>
  </div>
  <div class="am-body">
    <div class="am-sidebar" id="amSidebar">
      <h3>Input</h3>
      {{#each inputComponents}}
      <div class="am-sidebar-item" data-type="{{type}}" onclick="amAddComponent('{{type}}')">
        <span class="am-icon">{{icon}}</span>{{type}}
      </div>
      {{/each}}
      <h3>Display</h3>
      {{#each displayComponents}}
      <div class="am-sidebar-item" data-type="{{type}}" onclick="amAddComponent('{{type}}')">
        <span class="am-icon">{{icon}}</span>{{type}}
      </div>
      {{/each}}
      <h3>Media</h3>
      {{#each mediaComponents}}
      <div class="am-sidebar-item" data-type="{{type}}" onclick="amAddComponent('{{type}}')">
        <span class="am-icon">{{icon}}</span>{{type}}
      </div>
      {{/each}}
    </div>
    <div class="am-canvas-wrap" id="amCanvasWrap">
      <div class="am-canvas" id="amCanvas"></div>
      <button class="am-add-fab" onclick="amToggleAddMenu()">+</button>
      <div class="am-add-menu" id="amAddMenu">
        <h4>Input</h4>
        {{#each inputComponents}}
        <div class="am-add-menu-item" onclick="amAddComponent('{{type}}')">
          <span class="am-icon">{{icon}}</span>{{type}}
        </div>
        {{/each}}
        <h4>Display</h4>
        {{#each displayComponents}}
        <div class="am-add-menu-item" onclick="amAddComponent('{{type}}')">
          <span class="am-icon">{{icon}}</span>{{type}}
        </div>
        {{/each}}
        <h4>Media</h4>
        {{#each mediaComponents}}
        <div class="am-add-menu-item" onclick="amAddComponent('{{type}}')">
          <span class="am-icon">{{icon}}</span>{{type}}
        </div>
        {{/each}}
      </div>
    </div>
    <div class="am-props" id="amProps">
      <h3>Properties</h3>
      <div class="am-props-empty" id="amPropsEmpty">Click a widget to edit</div>
      <div id="amPropsForm" style="display:none"></div>
    </div>
  </div>
</div>
""")

BUILDER_JS = textwrap.dedent("""\
// ── State ──────────────────────────────────────────────────────────
let amItems = [];
let amSelectedId = null;
let amHistory = [];
let amIdCounter = 0;
let amDragging = null;   // { id, offsetX, offsetY }
let amResizing = null;   // { id, startX, startY, startW, startH }
const GRID = 20;

// ── Add Component ─────────────────────────────────────────────────
function amAddComponent(type) {
  amCloseAddMenu();
  amSaveHistory();
  const reg = window.__AM_REG__[type] || { icon: '📦', width: 200, height: 80, defaults: { label: type } };
  const id = 'w' + (++amIdCounter);
  // Find a free spot near center of visible area
  const wrap = document.getElementById('amCanvasWrap');
  const cx = wrap.scrollLeft + wrap.clientWidth / 2 - reg.width / 2;
  const cy = wrap.scrollTop + wrap.clientHeight / 2 - reg.height / 2;
  const x = Math.round(cx / GRID) * GRID;
  const y = Math.round(cy / GRID) * GRID;

  amItems.push({
    id, type,
    x: Math.max(0, x), y: Math.max(0, y),
    width: reg.width, height: reg.height,
    props: { ...reg.defaults }
  });
  amRender();
  amSelectWidget(id);
}

// ── Render All ────────────────────────────────────────────────────
function amRender() {
  const canvas = document.getElementById('amCanvas');
  canvas.innerHTML = '';
  amItems.forEach(item => {
    canvas.appendChild(amCreateWidget(item));
  });
}

// ── Create Widget DOM ─────────────────────────────────────────────
function amCreateWidget(item) {
  const reg = window.__AM_REG__[item.type] || { icon: '📦' };
  const el = document.createElement('div');
  el.className = 'am-widget' + (item.id === amSelectedId ? ' selected' : '');
  el.id = item.id;
  el.style.left = item.x + 'px';
  el.style.top = item.y + 'px';
  el.style.width = item.width + 'px';
  el.style.height = item.height + 'px';

  // Delete button
  const del = document.createElement('button');
  del.className = 'am-widget-del';
  del.textContent = '✕';
  del.onmousedown = (e) => { e.stopPropagation(); };
  del.onclick = (e) => { e.stopPropagation(); amRemoveWidget(item.id); };
  el.appendChild(del);

  // Header (drag handle)
  const header = document.createElement('div');
  header.className = 'am-widget-header';
  header.innerHTML = `<span class="am-icon">${reg.icon}</span>${item.type}`;
  el.appendChild(header);

  // Body preview
  const body = document.createElement('div');
  body.className = 'am-widget-body';
  body.innerHTML = amWidgetPreview(item);
  el.appendChild(body);

  // Resize handle
  const resize = document.createElement('div');
  resize.className = 'am-widget-resize';
  el.appendChild(resize);

  // ── Mouse drag ──
  header.addEventListener('mousedown', (e) => {
    e.preventDefault();
    amSelectWidget(item.id);
    const rect = el.getBoundingClientRect();
    amDragging = { id: item.id, offsetX: e.clientX - rect.left, offsetY: e.clientY - rect.top };
  });

  // Also allow drag from body
  el.addEventListener('mousedown', (e) => {
    if (e.target === del || e.target === resize) return;
    amSelectWidget(item.id);
  });

  // ── Touch drag ──
  header.addEventListener('touchstart', (e) => {
    e.preventDefault();
    amSelectWidget(item.id);
    const touch = e.touches[0];
    const rect = el.getBoundingClientRect();
    amDragging = { id: item.id, offsetX: touch.clientX - rect.left, offsetY: touch.clientY - rect.top, isTouch: true };
  }, { passive: false });

  // ── Resize ──
  resize.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    amSelectWidget(item.id);
    amResizing = { id: item.id, startX: e.clientX, startY: e.clientY, startW: item.width, startH: item.height };
  });

  resize.addEventListener('touchstart', (e) => {
    e.preventDefault();
    e.stopPropagation();
    amSelectWidget(item.id);
    const t = e.touches[0];
    amResizing = { id: item.id, startX: t.clientX, startY: t.clientY, startW: item.width, startH: item.height, isTouch: true };
  }, { passive: false });

  return el;
}

// ── Widget body preview ───────────────────────────────────────────
function amWidgetPreview(item) {
  const p = item.props;
  switch(item.type) {
    case 'Textbox':
      return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label||'Textbox'}</label><input type="text" placeholder="${p.placeholder||''}" />`;
    case 'Number':
      return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label||'Number'}</label><input type="text" value="${p.value||0}" />`;
    case 'Slider':
      return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label||'Slider'}</label><input type="range" min="${p.minimum||0}" max="${p.maximum||100}" value="${p.value||50}" /><div style="font-size:10px;color:#64748b;text-align:right">${p.value||50}</div>`;
    case 'Dropdown':
      return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label||'Dropdown'}</label><select>${(p.choices||[]).map(c=>'<option>'+c+'</option>').join('')}</select>`;
    case 'Checkbox':
      return `<label style="display:flex;align-items:center;gap:6px;font-size:12px"><input type="checkbox" ${p.value?'checked':''} /> ${p.label||'Checkbox'}</label>`;
    case 'Radio':
      return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label||'Radio'}</label>${(p.choices||[]).map(c=>'<label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="radio" name="'+item.id+'" />'+c+'</label>').join('')}`;
    case 'Button':
      return `<button class="am-btn-primary-prev" style="background:${p.variant==='primary'?'var(--am-primary)':'#e2e8f0'};color:${p.variant==='primary'?'white':'#1e293b'}">${p.label||'Button'}</button>`;
    case 'Markdown':
      return `<div style="font-size:12px;line-height:1.4;white-space:pre-wrap">${(p.value||'').substring(0,80)}</div>`;
    case 'Code':
      return `<div style="font-size:11px;background:#1e293b;color:#e2e8f0;padding:6px 8px;border-radius:4px;font-family:monospace;white-space:pre">${(p.value||'').substring(0,40)}</div>`;
    case 'Image':
    case 'Audio':
    case 'Video':
    case 'Gallery':
    case 'File':
      return `<div style="border:2px dashed #cbd5e1;border-radius:6px;height:calc(100% - 8px);display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:12px;min-height:40px">${(window.__AM_REG__[item.type]||{icon:'📦'}).icon} ${p.label||item.type}</div>`;
    case 'Chatbot':
      return `<div style="border:1px solid #e2e8f0;border-radius:6px;height:calc(100% - 8px);display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:11px">💬 Chat area</div>`;
    case 'JSON':
    case 'Label':
    case 'Dataframe':
      return `<div class="am-placeholder">${(window.__AM_REG__[item.type]||{icon:'📦'}).icon} ${p.label||item.type}</div>`;
    case 'HTML':
      return `<div style="font-size:12px">${(p.value||'').substring(0,60)}</div>`;
    default:
      return `<div class="am-placeholder">${p.label||item.type}</div>`;
  }
}

// ── Global mouse/touch move for dragging ──────────────────────────
document.addEventListener('mousemove', (e) => {
  if (amDragging && !amDragging.isTouch) amHandleDrag(e.clientX, e.clientY);
  if (amResizing && !amResizing.isTouch) amHandleResize(e.clientX, e.clientY);
});
document.addEventListener('mouseup', () => { amDragging = null; amResizing = null; });
document.addEventListener('touchmove', (e) => {
  if (amDragging && amDragging.isTouch) { e.preventDefault(); amHandleDrag(e.touches[0].clientX, e.touches[0].clientY); }
  if (amResizing && amResizing.isTouch) { e.preventDefault(); amHandleResize(e.touches[0].clientX, e.touches[0].clientY); }
}, { passive: false });
document.addEventListener('touchend', () => { amDragging = null; amResizing = null; });

function amHandleDrag(cx, cy) {
  const item = amItems.find(i => i.id === amDragging.id);
  if (!item) return;
  const canvas = document.getElementById('amCanvasWrap');
  const rect = canvas.getBoundingClientRect();
  let nx = cx - rect.left - amDragging.offsetX + canvas.scrollLeft;
  let ny = cy - rect.top - amDragging.offsetY + canvas.scrollTop;
  // Snap to grid
  nx = Math.round(nx / GRID) * GRID;
  ny = Math.round(ny / GRID) * GRID;
  item.x = Math.max(0, nx);
  item.y = Math.max(0, ny);
  // Update DOM directly (no full re-render)
  const el = document.getElementById(item.id);
  if (el) { el.style.left = item.x + 'px'; el.style.top = item.y + 'px'; }
}

function amHandleResize(cx, cy) {
  const item = amItems.find(i => i.id === amResizing.id);
  if (!item) return;
  let nw = amResizing.startW + (cx - amResizing.startX);
  let nh = amResizing.startH + (cy - amResizing.startY);
  nw = Math.max(120, Math.round(nw / GRID) * GRID);
  nh = Math.max(50, Math.round(nh / GRID) * GRID);
  item.width = nw;
  item.height = nh;
  const el = document.getElementById(item.id);
  if (el) { el.style.width = nw + 'px'; el.style.height = nh + 'px'; }
}

// ── Select / Props ────────────────────────────────────────────────
function amSelectWidget(id) {
  amSelectedId = id;
  // Update selection class
  document.querySelectorAll('.am-widget').forEach(w => w.classList.remove('selected'));
  const el = document.getElementById(id);
  if (el) el.classList.add('selected');
  amRenderProps();
}

function amRenderProps() {
  const form = document.getElementById('amPropsForm');
  const empty = document.getElementById('amPropsEmpty');
  if (!amSelectedId) { form.style.display = 'none'; empty.style.display = 'block'; return; }
  const item = amItems.find(i => i.id === amSelectedId);
  if (!item) { form.style.display = 'none'; empty.style.display = 'block'; return; }

  form.style.display = 'block';
  empty.style.display = 'none';

  let html = `<div class="am-prop-group"><label>Type</label><input value="${item.type}" disabled /></div>`;
  html += `<div class="am-prop-row"><div class="am-prop-group"><label>X</label><input type="number" value="${item.x}" onchange="amUpdatePos('x',Number(this.value))" /></div><div class="am-prop-group"><label>Y</label><input type="number" value="${item.y}" onchange="amUpdatePos('y',Number(this.value))" /></div></div>`;
  html += `<div class="am-prop-row"><div class="am-prop-group"><label>Width</label><input type="number" value="${item.width}" onchange="amUpdateSize('width',Number(this.value))" /></div><div class="am-prop-group"><label>Height</label><input type="number" value="${item.height}" onchange="amUpdateSize('height',Number(this.value))" /></div></div>`;

  const props = item.props || {};
  for (const [key, val] of Object.entries(props)) {
    if (key === 'choices') {
      html += `<div class="am-prop-group"><label>${key}</label><input value='${JSON.stringify(val)}' onchange="amUpdateProp('${key}',JSON.parse(this.value))" /></div>`;
    } else if (typeof val === 'boolean') {
      html += `<div class="am-prop-group"><label>${key}</label><select onchange="amUpdateProp('${key}',this.value==='true')"><option value="true" ${val?'selected':''}>True</option><option value="false" ${!val?'selected':''}>False</option></select></div>`;
    } else if (typeof val === 'number') {
      html += `<div class="am-prop-group"><label>${key}</label><input type="number" value="${val}" onchange="amUpdateProp('${key}',Number(this.value))" /></div>`;
    } else {
      html += `<div class="am-prop-group"><label>${key}</label><input value="${String(val).replace(/"/g,'&quot;')}" onchange="amUpdateProp('${key}',this.value)" /></div>`;
    }
  }
  form.innerHTML = html;
}

function amUpdateProp(key, value) {
  amSaveHistory();
  const item = amItems.find(i => i.id === amSelectedId);
  if (!item) return;
  item.props[key] = value;
  amRender();
}

function amUpdatePos(axis, val) {
  amSaveHistory();
  const item = amItems.find(i => i.id === amSelectedId);
  if (!item) return;
  item[axis] = Math.max(0, Math.round(val / GRID) * GRID);
  amRender();
}

function amUpdateSize(dim, val) {
  amSaveHistory();
  const item = amItems.find(i => i.id === amSelectedId);
  if (!item) return;
  item[dim] = Math.max(50, Math.round(val / GRID) * GRID);
  amRender();
}

// ── Actions ───────────────────────────────────────────────────────
function amRemoveWidget(id) {
  amSaveHistory();
  amItems = amItems.filter(i => i.id !== id);
  if (amSelectedId === id) amSelectedId = null;
  amRender();
  amRenderProps();
}

function amClear() {
  if (amItems.length === 0) return;
  amSaveHistory();
  amItems = [];
  amSelectedId = null;
  amRender();
  amRenderProps();
}

function amUndo() {
  if (amHistory.length === 0) return;
  amItems = amHistory.pop();
  amSelectedId = null;
  amRender();
  amRenderProps();
}

function amSaveHistory() {
  amHistory.push(JSON.parse(JSON.stringify(amItems)));
  if (amHistory.length > 30) amHistory.shift();
}

// ── Generate Code ─────────────────────────────────────────────────
function amGenerate() {
  const schema = { layout: amItems.map(i => ({ id: i.id, type: i.type, props: i.props, x: i.x, y: i.y, width: i.width, height: i.height })) };
  const schemaStr = JSON.stringify(schema);
  props.value = schemaStr;
  trigger('click', schemaStr);
}

// ── Add Menu (FAB) ────────────────────────────────────────────────
function amToggleAddMenu() {
  const menu = document.getElementById('amAddMenu');
  menu.classList.toggle('open');
}
function amCloseAddMenu() {
  const menu = document.getElementById('amAddMenu');
  menu.classList.remove('open');
}

// Close menu on outside click
document.addEventListener('click', (e) => {
  if (!e.target.closest('.am-add-fab') && !e.target.closest('.am-add-menu')) {
    amCloseAddMenu();
  }
});

// Click on canvas to deselect
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('amCanvas').addEventListener('mousedown', (e) => {
    if (e.target.id === 'amCanvas') { amSelectedId = null; document.querySelectorAll('.am-widget').forEach(w => w.classList.remove('selected')); amRenderProps(); }
  });
});

// ── Mobile panel toggle ──────────────────────────────────────────
function amTogglePanel(panel) {
  const sidebar = document.getElementById('amSidebar');
  const props = document.getElementById('amProps');
  if (panel === 'sidebar') {
    sidebar.style.display = sidebar.style.display === 'none' ? 'flex' : 'none';
    props.style.display = 'none';
  } else {
    props.style.display = props.style.display === 'none' ? 'block' : 'none';
    sidebar.style.display = 'none';
  }
}

// ── Keyboard shortcuts ────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
  if ((e.key === 'Delete' || e.key === 'Backspace') && amSelectedId) { amRemoveWidget(amSelectedId); }
  if (e.key === 'z' && (e.ctrlKey || e.metaKey)) { amUndo(); }
});

console.log('App Maker loaded ✅');
""")


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
    available_components = opts.get("components", list(COMPONENT_REGISTRY.keys()))
    theme_name = opts.get("theme", "soft")
    title = opts.get("title", "App Maker")

    filtered_registry = {
        k: v for k, v in COMPONENT_REGISTRY.items() if k in available_components
    }

    input_comps = [
        {"type": k, "icon": v["icon"], "category": v["category"]}
        for k, v in filtered_registry.items() if v["category"] == "input"
    ]
    display_comps = [
        {"type": k, "icon": v["icon"], "category": v["category"]}
        for k, v in filtered_registry.items() if v["category"] == "display"
    ]
    media_comps = [
        {"type": k, "icon": v["icon"], "category": v["category"]}
        for k, v in filtered_registry.items() if v["category"] == "media"
    ]

    registry_json = json.dumps(
        {k: {"icon": v["icon"], "width": v["width"], "height": v["height"], "defaults": v["defaults"]}
         for k, v in filtered_registry.items()}
    )

    with Blocks(title=title, fill_height=True) as demo:
        schema_state = State({"layout": []})

        builder = HTML(
            value="",
            html_template=BUILDER_HTML,
            css_template=BUILDER_CSS,
            js_on_load=f"""
            // 'click' event for generate
            window.__AM_REG__ = {registry_json};
            {BUILDER_JS}
            """,
            elem_id="app-maker-builder",
            min_height=700,
            props={
                "inputComponents": input_comps,
                "displayComponents": display_comps,
                "mediaComponents": media_comps,
            },
        )

        with Row():
            generate_btn = Button("✨ Generate Gradio Code", variant="primary", size="lg")
            run_btn = Button("🚀 Preview as Blocks", variant="secondary", size="lg")

        output_code = Code(
            label="Generated Gradio Code",
            language="python",
            interactive=True,
            lines=20,
        )

        preview_html = HTML(label="Preview", visible=False, min_height=300)

        def on_generate(evt_data) -> str:
            import json as _json
            schema = {"layout": []}
            if isinstance(evt_data, str):
                try:
                    schema = _json.loads(evt_data)
                except (ValueError, TypeError):
                    pass
            elif isinstance(evt_data, dict):
                schema = evt_data
            return _generate_code(schema)

        builder.click(on_generate, outputs=[output_code])

        def on_generate_btn():
            return _generate_code({"layout": []})

        generate_btn.click(on_generate_btn, outputs=[output_code])

        def on_run(code: str) -> tuple[str, dict]:
            if not code or not code.strip():
                return "No code to preview", {"layout": []}
            preview = _create_preview_html(code)
            return preview, {"layout": []}

        run_btn.click(on_run, inputs=[output_code], outputs=[preview_html, schema_state])

    return demo


def _create_preview_html(code: str) -> str:
    """Create an HTML preview of the generated Gradio code."""
    import re

    preview_parts = [
        '<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:20px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;">',
        '<h2 style="font-size:18px;margin-bottom:16px;color:#1e293b;">📱 App Preview</h2>',
        '<div style="background:white;border-radius:10px;padding:20px;border:1px solid #e2e8f0;">',
    ]

    components = re.findall(r'gr\.(\w+)\(([^)]*)\)', code)
    for comp_type, args_str in components:
        if comp_type in ('Blocks', 'Row', 'Column', 'Tabs', 'Tab', 'Group', 'Accordion'):
            continue
        label_match = re.search(r'label\s*=\s*["\']([^"\']*)["\']', args_str)
        label = label_match.group(1) if label_match else comp_type
        icon = COMPONENT_REGISTRY.get(comp_type, {}).get("icon", "📦")

        if comp_type == "Button":
            pos_match = re.search(r'["\']([^"\']*)["\']', args_str)
            if pos_match:
                label = pos_match.group(1)
            preview_parts.append(
                f'<div style="margin:8px 0;"><button style="background:#f97316;color:white;border:none;padding:10px 24px;border-radius:8px;font-size:14px;">{icon} {label}</button></div>'
            )
        elif comp_type == "Markdown":
            value_match = re.search(r'"""([^"]*)"""', args_str)
            value = value_match.group(1) if value_match else label
            preview_parts.append(f'<div style="margin:8px 0;padding:12px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;font-size:14px;">{icon} {value[:100]}</div>')
        elif comp_type in ("Image", "Audio", "Video", "Gallery"):
            preview_parts.append(f'<div style="margin:8px 0;"><div style="border:2px dashed #cbd5e1;border-radius:8px;padding:24px;text-align:center;color:#64748b;">{icon} {label}</div></div>')
        elif comp_type == "Slider":
            preview_parts.append(f'<div style="margin:8px 0;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">{icon} {label}</label><input type="range" min="0" max="100" value="50" style="width:100%;" disabled /></div>')
        elif comp_type == "Chatbot":
            preview_parts.append(f'<div style="margin:8px 0;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">{icon} {label}</label><div style="border:1px solid #e2e8f0;border-radius:8px;height:200px;padding:12px;background:#fafafa;color:#94a3b8;display:flex;align-items:center;justify-content:center;">Chat messages here</div></div>')
        else:
            preview_parts.append(f'<div style="margin:8px 0;"><label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px;">{icon} {label}</label><input type="text" placeholder="Enter {label}..." style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:13px;" disabled /></div>')

    preview_parts.append('</div>')
    preview_parts.append('<p style="font-size:12px;color:#94a3b8;margin-top:12px;text-align:center;">Copy the generated code to create the actual Gradio app.</p>')
    preview_parts.append('</div>')
    return ''.join(preview_parts)

<div align="center">
<a href="https://gradio.app">
<img src="readme_files/gradio.svg" alt="gradio" width=350>
</a>
</div>

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/gradio)](https://pypi.org/project/gradio/)
[![PyPI downloads](https://img.shields.io/pypi/dm/gradio)](https://pypi.org/project/gradio/)
![Python version](https://img.shields.io/badge/python-3.10+-important)
![Fork](https://img.shields.io/badge/fork-BF667-blue)

[Website](https://gradio.app)
| [Documentation](https://gradio.app/docs/)
| [Guides](https://gradio.app/guides/)
| [Upstream](https://github.com/gradio-app/gradio)

</div>

---

# Gradio BF667 Fork

This is the **BF667 fork** of [Gradio](https://github.com/gradio-app/gradio) — the open-source Python package that lets you build machine learning web apps in Python. This fork includes several enhancements, custom features, and optimizations that go beyond the upstream project, while maintaining full compatibility with the Gradio API you already know.

## What's Different from Upstream

### PrimeVue Integration

This fork adds a **PrimeVue bridge** (`js/primevue-bridge/`) that makes PrimeVue v4 components available as Web Components inside Gradio's Svelte 5 frontend. The bridge uses Vue 3's `defineCustomElement` API to wrap PrimeVue components, making them usable directly in Svelte templates without a separate Vue runtime. This opens up PrimeVue's full component library — data tables, calendars, pickers, trees, charts, and more — for use inside Gradio apps.

- Bridge package: `@gradio/primevue-bridge`
- Dual Vite plugin setup: `@vitejs/plugin-vue` (customElement mode) alongside `@sveltejs/vite-plugin-svelte`
- PrimeVue v4 with `@primevue/themes` for theming
- No conflicting Vue/Svelte runtimes — components are isolated Web Components

### Audio Loading Optimizations

The audio components have been heavily optimized for faster loading and smoother playback:

- **Lazy loading** of WaveSurfer.js and HLS.js — these heavy libraries are only loaded when an audio component actually appears on the page, reducing initial bundle size significantly
- **Web Worker for WAV encoding** — WAV file encoding is offloaded to a background thread, preventing UI freezes during audio processing
- **HLS buffer tuning** — optimized buffer settings for HLS streaming to reduce buffering time and improve playback start speed
- **Code splitting** via Vite `manualChunks` — audio-related dependencies are split into separate chunks so they don't block the main bundle

### Button Border Improvements

Subtle 1px borders have been added to all button variants across the Default, Ocean, Citrus, and Ember themes. This prevents the blur/bleeding visual effect that occurs between adjacent buttons when Gradio's glow effects are active, giving buttons cleaner visual separation without sacrificing the modern look.

### App Maker — Visual Drag-and-Drop Builder

A brand new **App Maker** module that provides a visual, free-form drag-and-drop interface for building Gradio apps directly in the browser:

```python
from gradio import app_maker

# Launch with defaults (all components, default theme)
demo = app_maker()
demo.launch()

# Or customize with options
demo = app_maker(options={
    "components": ["Textbox", "Slider", "Button", "Image", "Dropdown"],
    "theme": "soft",
    "title": "My App Builder"
})
demo.launch()
```

Features:
- **19 component types**: Textbox, Slider, Number, Checkbox, CheckboxGroup, Radio, Dropdown, Image, Video, Audio, File, DataFrame, Markdown, HTML, Code, JSON, Chatbot, Gallery, Plot
- **5 layout types**: Row, Column, Tab, Accordion, Group
- **Free-form canvas**: Components can be dragged and positioned anywhere on the canvas — no grid or flow constraints
- **Click-to-add**: Add components directly on the canvas by clicking from the palette
- **Code generation**: Automatically generates runnable Gradio Blocks code from your visual design
- **Mobile responsive**: Fully usable on phones and tablets with collapsible panels
- **Returns `gr.Blocks`**: The result is a standard Gradio Blocks object, so you can integrate it with any Gradio workflow

### Source Install Ready

This fork is designed to work when installed from source without requiring `pip install gradio`. Key fixes include:

- **`share=True` works from source**: Fixed `ValueError` about share mode only working with pip installs by adding `Path(__file__)` fallback resolution in `route_utils.py` and `routes.py`
- **Frontend templates included**: The `gradio/templates/frontend/` directory (627 files) is force-tracked in git, so template files like `frontend/share.html` are always available — no build step required for basic usage
- **GitHub Actions removed**: All `.github/workflows/*.yml` files and deployment history have been removed for a clean, standalone fork

---

## Installation

### From This Fork (Source Install)

```bash
git clone https://github.com/BF667/gradio.git
cd gradio
pip install -e .
```

### From PyPI (Upstream)

```bash
pip install --upgrade gradio
```

> **Note**: The PyPI package is the upstream Gradio release. To get this fork's enhancements, install from source as shown above.

---

## Quick Start

**Prerequisite**: Python 3.10 or higher.

### Basic Demo

```python
import gradio as gr

def greet(name, intensity):
    return "Hello, " + name + "!" * int(intensity)

demo = gr.Interface(
    fn=greet,
    inputs=["text", "slider"],
    outputs=["text"],
    api_name="predict"
)

demo.launch()
```

### Sharing Your Demo

```python
import gradio as gr

def greet(name):
    return "Hello " + name + "!"

demo = gr.Interface(fn=greet, inputs="textbox", outputs="textbox")

demo.launch(share=True)  # Works from source install too!
```

### Visual App Builder

```python
from gradio import app_maker

demo = app_maker()
demo.launch()
```

---

## Core Concepts

### Custom Demos with `gr.Blocks`

Gradio offers a low-level approach for designing web apps with more customizable layouts and data flows with the `gr.Blocks` class. Blocks supports controlling where components appear on the page, handling multiple data flows and complex interactions, and updating properties/visibility of components based on user interaction — still all in Python.

### Chatbots with `gr.ChatInterface`

Gradio includes `gr.ChatInterface`, specifically designed to create Chatbot UIs. Supply a function and Gradio creates a fully working chatbot interface.

### The Gradio Ecosystem

- [Gradio Python Client](https://www.gradio.app/guides/getting-started-with-the-python-client) (`gradio_client`): query any Gradio app programmatically in Python
- [Gradio JavaScript Client](https://www.gradio.app/guides/getting-started-with-the-js-client) (`@gradio/client`): query any Gradio app programmatically in JavaScript
- [Hugging Face Spaces](https://huggingface.co/spaces): the most popular place to host Gradio applications — for free
- [Server mode](https://www.gradio.app/guides/server-mode) (`gradio.Server`): build a custom frontend with Gradio's backend

---

## Themes

This fork ships with 4 built-in themes, all enhanced with subtle button borders for cleaner visual separation:

| Theme | Description |
|-------|-------------|
| **Default** | Clean, modern Gradio look with 1px button borders |
| **Ocean** | Cool blue tones with bordered buttons |
| **Citrus** | Warm orange/yellow palette with bordered buttons |
| **Ember** | Deep red/fire tones with bordered buttons |

---

## Open Source Stack

Gradio is built on top of many wonderful open-source libraries. This fork additionally uses:

[<img src="readme_files/huggingface_mini.svg" alt="huggingface" height=40>](https://huggingface.co)
[<img src="readme_files/python.svg" alt="python" height=40>](https://www.python.org)
[<img src="readme_files/fastapi.svg" alt="fastapi" height=40>](https://fastapi.tiangolo.com)
[<img src="readme_files/encode.svg" alt="encode" height=40>](https://www.encode.io)
[<img src="readme_files/svelte.svg" alt="svelte" height=40>](https://svelte.dev)
[<img src="readme_files/vite.svg" alt="vite" height=40>](https://vitejs.dev)
[<img src="readme_files/pnpm.svg" alt="pnpm" height=40>](https://pnpm.io)
[<img src="readme_files/tailwind.svg" alt="tailwind" height=40>](https://tailwindcss.com)

---

## License

Gradio is licensed under the Apache License 2.0 found in the [LICENSE](LICENSE) file in the root directory of this repository.

## Citation

If you use Gradio in your work, please cite:

```
@article{abid2019gradio,
  title = {Gradio: Hassle-Free Sharing and Testing of ML Models in the Wild},
  author = {Abid, Abubakar and Abdalla, Ali and Abid, Ali and Khan, Dawood and Alfozan, Abdulrahman and Zou, James},
  journal = {arXiv preprint arXiv:1906.02569},
  year = {2019},
}
```

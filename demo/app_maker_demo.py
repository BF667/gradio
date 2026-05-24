"""
Gradio Sketch Demo — Visual No-Code App Builder with Vibe Mode

Run this file to launch Gradio Sketch:
    python demo/app_maker_demo.py

Or use it in Python:
    from gradio import app_maker
    demo = app_maker()
    demo.launch()

Vibe Mode lets you describe what you want in natural language and
AI generates the Gradio code for you — just like gradio --vibe!
"""

from gradio import app_maker

if __name__ == "__main__":
    demo = app_maker(options={
        "components": [
            # Layout
            "Row", "Column", "Tabs", "Accordion",
            # Input
            "Textbox", "Number", "Slider", "Dropdown", "Checkbox", "Radio",
            # Action
            "Button",
            # Media
            "Image", "Audio", "Video", "File",
            # Output
            "Markdown", "Code", "JSON", "Chatbot", "Gallery", "Dataframe",
            "Label", "HTML",
        ],
        "theme": "soft",
        "title": "Gradio Sketch",
        "vibe": True,
    })
    demo.launch()

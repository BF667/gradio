"""
App Maker Demo — Visual Gradio App Builder

Run this file to launch the App Maker:
    python demo/app_maker_demo.py

Or use it in Python:
    from gradio import app_maker
    demo = app_maker()
    demo.launch()
"""

from gradio import app_maker

if __name__ == "__main__":
    demo = app_maker(options={
        "components": [
            "Textbox", "Number", "Slider", "Dropdown", "Checkbox", "Radio",
            "Button", "Image", "Audio", "Video", "File",
            "Markdown", "Code", "JSON", "Chatbot", "Gallery", "HTML",
        ],
        "theme": "soft",
        "title": "App Maker",
    })
    demo.launch()

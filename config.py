import json
import tkinter as tk
import os
import warnings

class Config:
    def __init__(self, config_path="config.json"):
        self.root = tk.Tk()
        self.model = tk.StringVar(value="deepseek-chat")
        self.streaming = tk.BooleanVar(value=True)
        self.system_prompt = tk.StringVar(value="You are pikachu! my assistant!. Respond in raw text without formatting symbols like ** or ## (THE ONLY EXCEPTION IS CODE BLOCKS OR COMMANDS. YOU CAN USE CODEBLOCKS FOR SCRIPTS AND WRAP COMMANDS IN CODE BLOCKS). You may use the ⚡ emoji")
        self.bg_color = "#1a1a1a"
        self.fg_color = "#e0e0e0"
        self.code_bg = "#2d2d2d"
        self.code_fg = "#e0e0e0"
        self.kaomoji_color = "#FF00FF"
        self.loading_color = "#8BE9FD"  # Bright for contrast
        self.green_border = "#FFFF00"
        self.output_font = ("Consolas", 10)  # Readable size
        self.text_font = ("Consolas", 10)   # Readable size
        self.loading_frames_list = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.kaomojis_list = [
            "⚡️^(˘ω˘)^ ==-------- ᶻ 𝗓 𐰁   !!",
            "⚡️^(ᵕωᵕ)^ --==------ ᶻ 𝗓 𐰁   !!",
            "⚡️^(˘ᵕ˘)^ ----==---- ᶻ 𝗓 𐰁   !!",
            "⚡️^(^ω^)^ ------==-- ᶻ 𝗓 𐰁   !!",
            "⚡️\\(^ω^)/ --------== ᶻ 𝗓 𐰁   !!"
        ]
        self.hide_scrollbars = True
        self.available_models = [
            {"name": "deepseek-chat", "api_key": "", "base_url": "https://api.deepseek.com/v1"},
            {"name": "deepseek-reasoner", "api_key": "", "base_url": "https://api.deepseek.com/v1"}
        ]

        self.load_config(config_path)
        self.root.destroy()

    def load_config(self, config_path):
        try:
            if not os.path.exists(config_path):
                # Generate default config.json
                default_config = {
                    "available_models": self.available_models,
                    "model": self.model.get(),
                    "streaming": self.streaming.get(),
                    "system_prompt": self.system_prompt.get(),
                    "bg_color": self.bg_color,
                    "fg_color": self.fg_color,
                    "code_bg": self.code_bg,
                    "code_fg": self.code_fg,
                    "kaomoji_color": self.kaomoji_color,
                    "loading_color": self.loading_color,
                    "green_border": self.green_border,
                    "output_font": list(self.output_font),
                    "text_font": list(self.text_font),
                    "loading_frames_list": self.loading_frames_list,
                    "kaomojis_list": self.kaomojis_list,
                    "hide_scrollbars": self.hide_scrollbars
                }
                with open(config_path, "w") as file:
                    json.dump(default_config, file, indent=2)
                print(f"Generated new config.json at {config_path}")
            else:
                # Load existing config.json
                with open(config_path, "r") as file:
                    config = json.load(file)
                    self.available_models = config.get("available_models", self.available_models)
                    self.model.set(config.get("model", self.model.get()))
                    self.streaming.set(config.get("streaming", self.streaming.get()))
                    self.system_prompt.set(config.get("system_prompt", self.system_prompt.get()))
                    self.bg_color = config.get("bg_color", self.bg_color)
                    self.fg_color = config.get("fg_color", self.fg_color)
                    self.code_bg = config.get("code_bg", self.code_bg)
                    self.code_fg = config.get("code_fg", self.code_fg)
                    self.kaomoji_color = config.get("kaomoji_color", self.kaomoji_color)
                    self.loading_color = config.get("loading_color", self.loading_color)
                    self.green_border = config.get("green_border", self.green_border)
                    self.output_font = tuple(config.get("output_font", self.output_font))
                    self.text_font = tuple(config.get("text_font", self.text_font))
                    self.loading_frames_list = config.get("loading_frames_list", self.loading_frames_list)
                    self.kaomojis_list = config.get("kaomojis_list", self.kaomojis_list)
                    self.hide_scrollbars = config.get("hide_scrollbars", self.hide_scrollbars)
        except Exception as e:
            print(f"Error handling config: {e}")

    def get_api_key(self):
        selected_model = self.model.get()
        for model in self.available_models:
            if model["name"] == selected_model:
                return model["api_key"]
        warnings.warn(f"No API key found for model: {selected_model}")
        return ""

    def get_base_url(self):
        selected_model = self.model.get()
        for model in self.available_models:
            if model["name"] == selected_model:
                return model["base_url"]
        warnings.warn(f"No base URL found for model: {selected_model}")
        return ""

    def get_available_model_names(self):
        return [model["name"] for model in self.available_models]
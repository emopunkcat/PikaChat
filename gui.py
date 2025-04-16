from tkinter import ttk, scrolledtext, messagebox
import tkinter as tk
import threading
import time
from config import Config
from api import APIHandler

class EmoChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EmoChat")
        self.root.geometry("1000x600")
        self.messages = []
        self.current_response = ""
        self.code_parse_buffer = ""
        self.in_code_block = False
        self.thinking_animation = False
        self.active_request = False
        self.stream_start_time = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.config = Config()
        self.root.configure(bg=self.config.bg_color)
        self.loading_frames = iter(self.config.loading_frames_list * 1000)
        self.kaomoji_waves = iter(self.config.kaomojis_list * 1000)
        self.api_handler = APIHandler(self)
        self.setup_ui()
        self.setup_keybindings()
        self.update_status_box()

    def setup_ui(self):
        style = ttk.Style()
        style.configure("Main.TFrame", background=self.config.bg_color)
        style.configure("TLabel", background=self.config.bg_color, foreground=self.config.fg_color)
        style.configure("TCombobox", fieldbackground=self.config.bg_color, foreground=self.config.fg_color)
        style.map("TCombobox", fieldbackground=[("readonly", self.config.bg_color)])

        main_frame = ttk.Frame(self.root, style="Main.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_bar_frame = ttk.Frame(main_frame, style="Main.TFrame")
        top_bar_frame.pack(fill=tk.X)
        top_bar_frame.grid_columnconfigure((0, 1), weight=1)

        text_widget_config = {
            "wrap": tk.NONE, "state": tk.DISABLED, "bg": self.config.bg_color,
            "fg": self.config.fg_color, "font": self.config.text_font, "relief": "flat",
            "highlightthickness": 1, "highlightcolor": self.config.green_border,
            "highlightbackground": self.config.green_border
        }

        self.thinking_box = tk.Text(top_bar_frame, height=1, padx=10, pady=5, **text_widget_config)
        self.thinking_box.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.status_box = tk.Text(top_bar_frame, height=1, padx=10, pady=5, **text_widget_config)
        self.status_box.grid(row=0, column=1, sticky="ew", padx=(5, 5))

        ttk.Label(top_bar_frame, text="Model:", style="TLabel").grid(row=0, column=2, sticky="w", padx=(0, 5))
        model_names = self.config.get_available_model_names()
        if self.config.model.get() not in model_names:
            self.config.model.set(model_names[0] if model_names else "deepseek-chat")
        self.model_selector = ttk.Combobox(
            top_bar_frame, textvariable=self.config.model, values=model_names,
            state="readonly", width=15, font=self.config.text_font
        )
        self.model_selector.grid(row=0, column=3, sticky="w")
        self.model_selector.bind("<<ComboboxSelected>>", lambda e: self.config.model.set(self.model_selector.get()))

        self.chat_display = tk.Text(
            main_frame, wrap=tk.WORD, state="disabled", bg=self.config.bg_color, fg=self.config.fg_color,
            font=self.config.output_font, insertbackground=self.config.fg_color, selectbackground=self.config.code_bg,
            padx=10, pady=10, tabs=("500 right"), relief="flat", highlightthickness=1,
            highlightcolor=self.config.green_border, highlightbackground=self.config.green_border
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.Frame(main_frame, style="Main.TFrame")
        input_frame.pack(fill=tk.X, pady=(5, 0))

        input_border_frame = tk.Frame(input_frame, bg=self.config.green_border, highlightthickness=1,
                                      highlightbackground=self.config.green_border, highlightcolor=self.config.green_border)
        input_border_frame.pack(fill=tk.BOTH, expand=True)

        self.user_input = tk.Text(
            input_border_frame, wrap=tk.WORD, height=4, bg=self.config.bg_color, fg=self.config.fg_color,
            font=self.config.text_font, insertbackground=self.config.fg_color, selectbackground=self.config.code_bg,
            padx=10, pady=10, relief="flat"
        ) if self.config.hide_scrollbars else scrolledtext.ScrolledText(
            input_border_frame, wrap=tk.WORD, height=4, bg=self.config.bg_color, fg=self.config.fg_color,
            font=self.config.text_font, insertbackground=self.config.fg_color, selectbackground=self.config.code_bg,
            padx=10, pady=10, relief="flat"
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if not self.config.hide_scrollbars:
            self.user_input.vbar.config(troughcolor=self.config.bg_color, background=self.config.code_bg)

        send_label = tk.Label(input_border_frame, text="[SEND]", bg=self.config.bg_color, fg=self.config.green_border,
                              font=self.config.text_font, cursor="hand2")
        send_label.pack(side=tk.RIGHT, padx=(5, 10), pady=10)
        send_label.bind("<Button-1>", lambda e: self.send_message())

        self.status_bar = ttk.Label(
            self.root, text="⚡️ !(^_^) Ready!", relief=tk.FLAT, anchor=tk.W, font=("Consolas", 10),
            background=self.config.bg_color, foreground=self.config.kaomoji_color, padding=5
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.configure_text_tags()

    def configure_text_tags(self):
        tags = {
            "user": {"foreground": "#4fc3f7"},
            "assistant": {"foreground": self.config.fg_color},
            "code": {"background": self.config.code_bg, "foreground": self.config.code_fg},
            "kaomoji": {"foreground": self.config.kaomoji_color},
            "error": {"foreground": "#f44336"},
            "loading_text": {"foreground": self.config.loading_color},
            "status": {"foreground": self.config.fg_color}
        }
        for tag, config in tags.items():
            for widget in (self.chat_display, self.thinking_box, self.status_box):
                widget.tag_configure(tag, **config)
        
        # Add binding for code blocks
        self.chat_display.tag_bind("code", "<Button-1>", self.show_code_popup)

    def show_code_popup(self, event):
        # Get the clicked code block
        clicked_pos = f"@{event.x},{event.y}"
        start_idx = self.chat_display.index(f"{clicked_pos} linestart")
        end_idx = self.chat_display.index(f"{clicked_pos} lineend")
        
        # Expand selection to entire code block
        while "code" in self.chat_display.tag_names(start_idx + " -1c"):
            start_idx = self.chat_display.index(f"{start_idx} -1l linestart")
        
        while "code" in self.chat_display.tag_names(end_idx + " +1c"):
            end_idx = self.chat_display.index(f"{end_idx} +1l lineend")
        
        # Extract the code content
        code_content = self.chat_display.get(start_idx, end_idx)
        
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title("Code Block")
        popup.geometry("800x600")
        popup.configure(bg=self.config.bg_color)
        
        # Add scrolled text widget for code
        code_frame = tk.Frame(popup, bg=self.config.green_border)
        code_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        code_text = scrolledtext.ScrolledText(
            code_frame, wrap=tk.NONE, bg=self.config.code_bg, fg=self.config.code_fg,
            font=self.config.text_font, insertbackground=self.config.fg_color,
            padx=10, pady=10, relief="flat"
        )
        code_text.pack(fill=tk.BOTH, expand=True)
        code_text.insert(tk.END, code_content)
        code_text.config(state=tk.DISABLED)
        
        # Add copy button
        button_frame = tk.Frame(popup, bg=self.config.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        copy_button = tk.Button(
            button_frame, text="Copy to Clipboard", command=lambda: self.copy_to_clipboard(code_content),
            bg=self.config.bg_color, fg=self.config.fg_color, activebackground=self.config.code_bg,
            activeforeground=self.config.code_fg, relief="flat", font=self.config.text_font
        )
        copy_button.pack(side=tk.RIGHT, padx=5)
        
        close_button = tk.Button(
            button_frame, text="Close", command=popup.destroy,
            bg=self.config.bg_color, fg=self.config.fg_color, activebackground=self.config.code_bg,
            activeforeground=self.config.code_fg, relief="flat", font=self.config.text_font
        )
        close_button.pack(side=tk.RIGHT, padx=5)

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_bar.config(text="⚡️ Code copied to clipboard! ⚡️")
        self.root.after(3000, lambda: self.update_status())

    def update_status_box(self):
        self.status_box.config(state=tk.NORMAL)
        self.status_box.delete(1.0, tk.END)
        self.status_box.insert(tk.END, f"Ping: {self.api_handler.get_ping_time()} | Time: {self.api_handler.get_current_time()}", "status")
        self.status_box.config(state=tk.DISABLED)
        self.root.after(1000, self.update_status_box)

    def setup_keybindings(self):
        self.user_input.bind("<Return>", lambda e: self.send_message() if not (e.state & 0x1) else None)
        self.user_input.bind("<Shift-Return>", lambda e: "break")
        self.user_input.bind("<KeyRelease>", self.adjust_input_height)
        self.user_input.focus_set()

    def adjust_input_height(self, event):
        lines = self.user_input.get("1.0", "end-1c").count("\n") + 1
        self.user_input.configure(height=min(max(lines, 3), 8))

    def update_display(self, text, tag=None):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, text, tag)
        self.chat_display.yview(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def manage_thinking_animation(self, state=None):
        if state == "start":
            self.thinking_animation = True
            self.thinking_box.config(state=tk.NORMAL)
            self.thinking_box.delete(1.0, tk.END)
            self.thinking_box.insert(tk.END, "pika.. ", "loading_text")
            self.thinking_box.insert(tk.END, next(self.loading_frames), "loading_text")
            self.thinking_box.insert(tk.END, "  ⚡️(>^ω^<)", "kaomoji")
            self.thinking_box.config(state=tk.DISABLED)
            self._animate_thinking()
        elif state == "stop":
            self.thinking_animation = False
            self.thinking_box.config(state=tk.NORMAL)
            self.thinking_box.delete(1.0, tk.END)
            self.thinking_box.config(state=tk.DISABLED)
            self.root.after(100, self._animate_idle_kaomoji)
        elif self.thinking_animation:
            self.thinking_box.config(state=tk.NORMAL)
            loading_pos = self.thinking_box.tag_ranges("loading_text")
            if loading_pos:
                last_char = f"{loading_pos[1]}-1c"
                self.thinking_box.delete(last_char, loading_pos[1])
                self.thinking_box.insert(last_char, next(self.loading_frames), "loading_text")
            self.thinking_box.config(state=tk.DISABLED)
            self.root.after(200, self.manage_thinking_animation)

    def _animate_idle_kaomoji(self):
        if not self.thinking_animation and not self.active_request:
            self.thinking_box.config(state=tk.NORMAL)
            self.thinking_box.delete(1.0, tk.END)
            self.thinking_box.insert(tk.END, next(self.kaomoji_waves), "kaomoji")
            self.thinking_box.config(state=tk.DISABLED)
            self.root.after(500, self._animate_idle_kaomoji)

    def _animate_thinking(self):
        if self.thinking_animation:
            self.manage_thinking_animation()

    def send_message(self):
        if self.active_request:
            return "break"
        user_text = self.user_input.get("1.0", tk.END).strip()
        if not user_text:
            return "break"
        self.active_request = True
        self.user_input.delete("1.0", tk.END)
        self.update_display(f"\n>: {user_text}\n", "user")
        self.manage_thinking_animation("start")
        threading.Thread(target=self.api_handler.process_request, args=(user_text,)).start()
        return "break"

    def update_status(self):
        elapsed = time.time() - self.stream_start_time
        total_context_tokens = self.input_tokens + self.output_tokens
        self.status_bar.config(text=f"⚡️ !(^_^) Tokens: {self.input_tokens} in / {self.output_tokens} out "
                                   f"(Total: {total_context_tokens}) | Response time: {elapsed:.2f}s | "
                                   f"WITH <3 EMO PUNK CAT =⩊=")

    def show_error(self, message):
        print(f"Showing error: {message}")
        self.root.after(0, lambda: messagebox.showerror("Error", message))
        self.update_display(f"\nERROR: {message}\n", "error")
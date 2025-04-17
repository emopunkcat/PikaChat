from tkinter import ttk, scrolledtext, messagebox, filedialog
import tkinter as tk
import threading
import time
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token
from config import Config  # Ensure correct import
from api import APIHandler  # Ensure correct import
import os
import re

from pygments.lexers import get_lexer_by_name
from pygments import lex
from pygments.token import Token

class SyntaxHighlighter:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.lexer = get_lexer_by_name("python")  # Default to Python
        self.setup_tags()  # Configure tags upfront
        self.bind_events()

    def setup_tags(self):
        """Define and configure tags for syntax highlighting."""
        self.text_widget.tag_configure("keyword", foreground="#FF0000")  # Red
        self.text_widget.tag_configure("function", foreground="#0000FF")  # Blue
        self.text_widget.tag_configure("string", foreground="#00AA00")  # Green
        self.text_widget.tag_configure("comment", foreground="#888888")  # Gray
        self.text_widget.tag_configure("number", foreground="#AA00AA")  # Purple

    def bind_events(self):
        """Bind events for typing, pasting, and content changes."""
        self.text_widget.bind("<KeyRelease>", lambda e: self.highlight())
        self.text_widget.bind("<<Paste>>", lambda e: self.text_widget.after(10, self.highlight))

    def highlight(self):
        """Apply syntax highlighting to the entire content."""
        code = self.text_widget.get("1.0", "end-1c")
        if not code.strip():
            return  # Skip empty content

        # Clear existing tags
        for tag in self.text_widget.tag_names():
            self.text_widget.tag_remove(tag, "1.0", "end")

        # Tokenize and highlight
        start_pos = "1.0"
        for token, content in lex(code, self.lexer):
            if not content:
                continue  # Skip empty tokens
            end_pos = f"{start_pos}+{len(content)}c"
            self.apply_highlight(token, content, start_pos, end_pos)
            start_pos = end_pos  # Update position for next token

    def apply_highlight(self, token, content, start_pos, end_pos):
        """Apply highlighting for a single token."""
        if token in Token.Keyword:
            self.text_widget.tag_add("keyword", start_pos, end_pos)
        elif token in Token.Name.Function:
            self.text_widget.tag_add("function", start_pos, end_pos)
        elif token in Token.String:
            self.text_widget.tag_add("string", start_pos, end_pos)
        elif token in Token.Comment:
            self.text_widget.tag_add("comment", start_pos, end_pos)
        elif token in Token.Number:
            self.text_widget.tag_add("number", start_pos, end_pos)

class EmoChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EmoChat IDE")  # Update title
        self.root.geometry("1200x800")  # Increase size
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
        self.current_directory = None  # Store current directory
        self.current_file_path = None #Store the current file path
        self.setup_ui()
        self.setup_keybindings()
        self.update_info_box()

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
        self.create_menu_bar()
        top_bar_frame.grid_columnconfigure((0, 1), weight=1)

        text_widget_config = {
            "wrap": tk.NONE, "state": tk.DISABLED, "bg": self.config.bg_color,
            "fg": self.config.fg_color, "font": self.config.text_font, "relief": "flat",
            "highlightthickness": 1, "highlightcolor": self.config.green_border,
            "highlightbackground": self.config.green_border
        }

        # ------------------ UI FRAME ---------------------
        content_frame = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL, style="Main.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # ------------------ File Navigation ---------------------
        self.file_pane = ttk.Frame(content_frame)
        content_frame.add(self.file_pane, weight=1)  # Leftmost pane (3/6 = 50%)

        self.file_list = tk.Listbox(
            self.file_pane,
            bg=self.config.bg_color,
            fg=self.config.fg_color,
            font=self.config.text_font,
            selectbackground=self.config.code_bg,
            selectforeground=self.config.fg_color,
            highlightthickness=1,
            highlightcolor=self.config.green_border,
            highlightbackground=self.config.green_border
        )
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self.file_list.bind("<Double-Button-1>", self.open_file)

        # ------------------ File Editor ---------------------
        self.editor_pane = ttk.Frame(content_frame)
        content_frame.add(self.editor_pane, weight=1)  # Middle pane (1/6 ≈ 16.67%)

        self.file_content = tk.Text(
            self.editor_pane,
            wrap=tk.WORD,
            bg=self.config.bg_color,
            fg=self.config.fg_color,
            font=self.config.output_font,
            insertbackground=self.config.fg_color,
            selectbackground=self.config.code_bg,
            padx=10,
            pady=10,
            tabs=("500 right"),
            relief="flat",
            highlightthickness=1,
            highlightcolor=self.config.green_border,
            highlightbackground=self.config.green_border,
            state=tk.NORMAL
        )
        self.file_content.pack(fill=tk.BOTH, expand=True)
        self.file_content.bind("<ButtonRelease-1>", self.send_selected_text)

        # Initialize syntax highlighting
        self.highlighter = SyntaxHighlighter(self.file_content)

        # ------------------ Chat Display ---------------------
        self.chat_pane = ttk.Frame(content_frame)
        content_frame.add(self.chat_pane, weight=1)  # Right pane (2/6 ≈ 33.33%)

        self.chat_display = tk.Text(
            self.chat_pane,
            wrap=tk.WORD,
            state="disabled",
            bg=self.config.bg_color,
            fg=self.config.fg_color,
            font=self.config.output_font,
            insertbackground=self.config.fg_color,
            selectbackground=self.config.code_bg,
            padx=10,
            pady=10,
            tabs=("500 right"),
            relief="flat",
            highlightthickness=1,
            highlightcolor=self.config.green_border,
            highlightbackground=self.config.green_border
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        #self.highlighter = SyntaxHighlighter(self.chat_display)


        # ------------------ Status Box setup ---------------------
        thinking_animation_config = {"wrap": tk.NONE, "state": tk.DISABLED, "bg": self.config.bg_color,
                       "fg": self.config.fg_color, "font": ("Consolas", 8), "relief": "flat",
                       "highlightthickness": 1, "highlightcolor": self.config.green_border,
                       "highlightbackground": self.config.green_border, "width": 50, "height": 1}
        self.thinking_animation_box = tk.Text(top_bar_frame,  **thinking_animation_config)
        self.thinking_animation_box.grid(row=0, column=0, sticky="w", padx=(0, 5))

        network_info_config =  {"wrap": tk.NONE, "state": tk.DISABLED, "bg": self.config.bg_color,
                       "fg": self.config.fg_color, "font": ("Consolas", 8), "relief": "flat",
                       "highlightthickness": 1, "highlightcolor": self.config.green_border,
                       "highlightbackground": self.config.green_border, "width": 50, "height": 1}
        self.network_info_box = tk.Text(top_bar_frame, **network_info_config)
        self.network_info_box.grid(row=0, column=1, sticky="w", padx=(5, 5))

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

        # -------NEW prompt box setup--------
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

        # Renamed it
        self.bottom_status_bar = ttk.Label(
            self.root, text="⚡️ !(^_^) Ready!", relief=tk.FLAT, anchor=tk.W, font=("Consolas", 10),
            background=self.config.bg_color, foreground=self.config.kaomoji_color, padding=5
        )
        self.bottom_status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.configure_text_tags()

    def create_menu_bar(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        file_menu.add_separator() # Adds dividing line
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu_bar)

    def open_folder(self):
        directory = filedialog.askdirectory(initialdir=".", title="Select Directory")
        if directory:
            self.current_directory = directory
            self.populate_file_list()

    def populate_file_list(self):
        self.file_list.delete(0, tk.END)
        if not self.current_directory:
            return

        try:
            for root, dirs, files in os.walk(self.current_directory):
                # Calculate the indentation level based on directory depth
                level = root.replace(self.current_directory, '').count(os.sep)
                indent = '  ' * level

                # Insert the current directory (if not the root)
                if level > 0:
                    dir_name = os.path.basename(root)
                    self.file_list.insert(tk.END, f"{indent}{dir_name}/")

                # Insert files in the current directory
                for file in files:
                    self.file_list.insert(tk.END, f"{indent}{file}")

        except OSError as e:
            messagebox.showerror("Error", f"Could not read directory:\n{e}")

    def open_file(self, event):
        if not self.current_directory:
            return
        selection = self.file_list.curselection()
        if selection:
            # Get the displayed filename and clean it
            displayed_name = self.file_list.get(selection[0])
            
            # Remove indentation and icons
            clean_name = displayed_name.lstrip().replace("📁 ", "").replace("📄 ", "")
            
            # Handle directory paths (ending with /)
            if clean_name.endswith("/"):
                clean_name = clean_name[:-1]
            
            filepath = os.path.join(self.current_directory, clean_name)
            
            try:
                if os.path.isdir(filepath):
                    # Don't try to open directories
                    return
                
                with open(filepath, "r") as f:  # Open the file with error handling
                    content = f.read()  # Read file contents safely
                    self.file_content.delete(1.0, tk.END)
                    self.file_content.insert(1.0, content)
                    self.current_file_path = filepath
            except OSError as e:
                messagebox.showerror("Error", f"Could not open/read file:\n{e}")
            except UnicodeDecodeError as e:
                messagebox.showerror("Error", f"Could not decode file:\n{e}")

    def send_selected_text(self, event):
        try:
            selected_text = self.file_content.get(tk.SEL_FIRST, tk.SEL_LAST) #Get the editor
            self.user_input.insert(tk.END, selected_text)
        except tk.TclError: #No text was selected
            pass

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
            for widget in (self.chat_display, self.thinking_animation_box, self.network_info_box):
                widget.tag_configure(tag, **config)

        self.chat_display.tag_bind("code", "<Button-1>", self.show_code_popup)

    def show_code_popup(self, event):
        clicked_pos = f"@{event.x},{event.y}"
        start_idx = self.chat_display.index(f"{clicked_pos} linestart")
        end_idx = self.chat_display.index(f"{clicked_pos} lineend")

        while "code" in self.chat_display.tag_names(start_idx + " -1c"):
            start_idx = self.chat_display.index(f"{start_idx} -1l linestart")

        while "code" in self.chat_display.tag_names(end_idx + " +1c"):
            end_idx = self.chat_display.index(f"{end_idx} +1l lineend")

        code_content = self.chat_display.get(start_idx, end_idx)

        popup = tk.Toplevel(self.root)
        popup.title("Code Block")
        popup.geometry("800x600")
        popup.configure(bg=self.config.bg_color)

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
        self.bottom_status_bar.config(text="⚡️ Code copied to clipboard! ⚡️")
        self.root.after(3000, lambda: self.update_status())

    def update_info_box(self):
        self.network_info_box.config(state=tk.NORMAL)
        self.network_info_box.delete(1.0, tk.END)
        self.network_info_box.insert(tk.END, f"Ping: {self.api_handler.get_ping_time()} | Time: {self.api_handler.get_current_time()}", "status")
        self.network_info_box.config(state=tk.DISABLED)
        self.root.after(1000, self.update_info_box)

    def setup_keybindings(self):
        print("Setting up keybindings")
        self.root.bind("<Alt_R>", lambda e: self.clear_output())
        self.root.bind("<Return>", lambda e: self.send_message() if not (e.state & 0x0001) else None)
        self.user_input.bind("<Shift-Return>", lambda e: self.user_input.insert(tk.INSERT, "\n"))
        self.user_input.bind("<KeyRelease>", self.adjust_input_height)
        self.user_input.focus_set()

    def clear_output(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.messages = []
        self.current_response = ""
        self.input_tokens = 0
        self.output_tokens = 0
        self.bottom_status_bar.config(text="⚡️ !(^_^) Chat cleared! Ready for a new convo!")
        self.root.after(3000, self.update_status)
        return "break"

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
            self.thinking_animation_box.config(state=tk.NORMAL)
            self.thinking_animation_box.delete(1.0, tk.END)
            self.thinking_animation_box.insert(tk.END, "pika.. ", "loading_text")
            self.thinking_animation_box.insert(tk.END, next(self.loading_frames), "loading_text")
            self.thinking_animation_box.insert(tk.END, "  ⚡️(>^ω^<)", "kaomoji")
            self.thinking_animation_box.config(state=tk.DISABLED)
            self._animate_thinking()
        elif state == "stop":
            self.thinking_animation = False
            self.thinking_animation_box.config(state=tk.NORMAL)
            self.thinking_animation_box.delete(1.0, tk.END)
            self.thinking_animation_box.config(state=tk.DISABLED)
            self.root.after(100, self._animate_idle_kaomoji)
        elif self.thinking_animation:
            self.thinking_animation_box.config(state=tk.NORMAL)
            loading_pos = self.thinking_animation_box.tag_ranges("loading_text")
            if loading_pos:
                last_char = f"{loading_pos[1]}-1c"
                self.thinking_animation_box.delete(last_char, loading_pos[1])
                self.thinking_animation_box.insert(last_char, next(self.loading_frames), "loading_text")
            self.thinking_animation_box.config(state=tk.DISABLED)
            self.root.after(200, self.manage_thinking_animation)

    def _animate_idle_kaomoji(self):
        if not self.thinking_animation and not self.active_request:
            self.thinking_animation_box.config(state=tk.NORMAL)
            self.thinking_animation_box.delete(1.0, tk.END)
            self.thinking_animation_box.insert(tk.END, next(self.kaomoji_waves), "kaomoji")
            self.thinking_animation_box.config(state=tk.DISABLED)
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
        self.user_input.delete(1.0, tk.END)
        self.update_display(f"\n>: {user_text}\n", "user")
        self.manage_thinking_animation("start")
        threading.Thread(target=self.api_handler.process_request, args=(user_text,)).start()
        return "break"

    def update_status(self):
        elapsed = time.time() - self.stream_start_time
        total_context_tokens = self.input_tokens + self.output_tokens
        self.bottom_status_bar.config(text=f"⚡️ !(^_^) Tokens: {self.input_tokens} in / {self.output_tokens} out "
                                   f"(Total: {total_context_tokens}) | Response time: {elapsed:.2f}s | "
                                   f"WITH <3 EMO PUNK CAT =⩊=")

    def show_error(self, message):
        print(f"Showing error: {message}")
        self.root.after(0, lambda: messagebox.showerror("Error", message))
        self.update_display(f"\nERROR: {message}\n", "error")
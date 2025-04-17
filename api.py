from openai import OpenAI
import time
import requests
from datetime import datetime
import tkinter as tk

DEBUG_MODE = False  # Global debug toggle

class APIHandler:
    def __init__(self, gui):
        self.gui = gui
        self.log("APIHandler initialized")

    def log(self, message):
        if DEBUG_MODE:
            print(f"[DEBUG API]: {message}")

    def get_ping_time(self):
        try:
            start_time = time.time()
            base_url = self.gui.config.get_base_url()
            self.log(f"Pinging base URL: {base_url}")
            response = requests.get(base_url, timeout=5)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            ping_ms = (time.time() - start_time) * 1000
            ping_str = f"{ping_ms:.0f}ms"
            self.log(f"Ping time: {ping_str}")
            return ping_str
        except requests.exceptions.RequestException as e:
            self.log(f"Ping error: {e}")
            return "N/A"
        except Exception as e:
            self.log(f"Unexpected ping error: {e}") #More general error
            return "N/A"

    def get_current_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.log(f"Current time: {current_time}")
        return current_time

    def get_chat_history(self):
        """Extract conversation history from chat_display."""
        self.log("Extracting chat history")
        history = [{"role": "system", "content": self.gui.config.system_prompt.get()}]
        chat_content = self.gui.chat_display.get(1.0, tk.END).strip()
        if not chat_content:
            self.log("Chat content is empty, returning only system prompt.")
            return history
        lines = chat_content.split("\n")
        current_role = None
        current_message = []
        for line in lines:
            if line.startswith(">: "):  # User message
                if current_message and current_role:
                    history.append({"role": current_role, "content": "\n".join(current_message).strip()})
                current_role = "user"
                current_message = [line[3:]]  # Remove ">: "
            elif line.startswith("ERROR: "):  # Skip errors
                continue
            else:  # Assistant message or continuation
                if current_role is None and line.strip():
                    current_role = "assistant"
                    current_message = [line]
                elif current_role:
                    current_message.append(line)
        if current_message and current_role:
            history.append({"role": current_role, "content": "\n".join(current_message).strip()})
        self.log(f"Extracted chat history: {history}")
        return history

    def process_request(self, user_text):
        self.log("Starting process_request")
        try:
            api_key = self.gui.config.get_api_key()
            base_url = self.gui.config.get_base_url()
            self.log(f"API Key: {api_key[:4]}...{api_key[-4:] if api_key else ''}, Base URL: {base_url}") #Sanitize for logging
            if not api_key or not base_url:
                raise ValueError("Invalid API key or base URL for selected model")
            client = OpenAI(api_key=api_key, base_url=base_url)
            messages = self.get_chat_history()
            if user_text.strip():
                messages.append({"role": "user", "content": user_text})
            self.gui.input_tokens = sum(len(m["content"].split()) for m in messages)
            self.log(f"Input tokens: {self.gui.input_tokens}")
            self.gui.stream_start_time = time.time()
            self.log(f"StreamStartTime: {self.gui.stream_start_time}")
            response = client.chat.completions.create(
                model=self.gui.config.model.get(),
                messages=messages,
                stream=self.gui.config.streaming.get(),
                max_tokens=8096
            )
            self.log("API call successful, handling response")
            self.handle_response(response)
        except Exception as e:
            self.log(f"Error in process_request: {str(e)}")
            self.gui.show_error(f"API Error: {str(e)}")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")
            return
        finally:
            self.log("Executing finally block in process_request")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")

    def handle_response(self, response):
            self.log("Starting handle_response")
            self.log(f"parse_and_display_content available: {hasattr(self, 'parse_and_display_content')}")
            self.gui.current_response = ""
            self.gui.update_display("\n> ", "assistant")
            try:
                streaming_enabled = self.gui.config.streaming.get()
                self.log(f"Streaming Enabled: {streaming_enabled}")
                if streaming_enabled:
                    self.log("Handling streaming response")
                    total_characters = 0  # Initialize character counter
                    for chunk in response:
                        content = chunk.choices[0].delta.content or ""
                        self.gui.current_response += content
                        self.parse_and_display_content(content)
                        total_characters += len(content) #Increment character counter inside
                    self.gui.output_tokens = total_characters / 4 #Character counter divided by 4
                else:
                    self.log("Handling non-streaming response")
                    full_response = response.choices[0].message.content
                    self.gui.current_response = full_response
                    self.parse_and_display_content(full_response)
                    self.gui.output_tokens = len(full_response) / 4
                self.gui.output_tokens = int(self.gui.output_tokens) #Convert to integer for ease of use
                self.log(f"Output tokens: {self.gui.output_tokens}")
                self.gui.update_status()
                self.log("Completed handle_response successfully")
            except Exception as e:
                self.log(f"Error in handle_response: {str(e)}")
                self.gui.show_error(f"Response Error: {str(e)}")
                self.gui.active_request = False
                self.gui.manage_thinking_animation("stop")
                raise

    def parse_and_display_content(self, content):
        self.log("Entering parse_and_display_content")
        self.gui.code_parse_buffer += content
        while True:
            if self.gui.in_code_block:
                end_idx = self.gui.code_parse_buffer.find('```')
                if end_idx == -1:
                    self.log("In code block, end not found, displaying buffer")
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer, "code")
                    self.gui.code_parse_buffer = ""
                    break
                else:
                    self.log("In code block, end found, displaying code")
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer[:end_idx], "code")
                    self.gui.code_parse_buffer = self.gui.code_parse_buffer[end_idx+3:]
                    self.gui.in_code_block = False
            else:
                start_idx = self.gui.code_parse_buffer.find('```')
                if start_idx == -1:
                    self.log("Not in code block, start not found, displaying assistant text")
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer, "assistant")
                    self.gui.code_parse_buffer = ""
                    break
                else:
                    self.log("Not in code block, start found, displaying assistant text")
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer[:start_idx], "assistant")
                    self.gui.code_parse_buffer = self.gui.code_parse_buffer[start_idx+3:]
                    self.gui.in_code_block = True
from openai import OpenAI
import time
import requests
from datetime import datetime
import tkinter as tk

class APIHandler:
    def __init__(self, gui):
        self.gui = gui
        print("APIHandler initialized")  # Debug print

    def get_ping_time(self):
        try:
            start_time = time.time()
            requests.get(self.gui.config.get_base_url(), timeout=5)
            ping_ms = (time.time() - start_time) * 1000
            return f"{ping_ms:.0f}ms"
        except:
            return "N/A"

    def get_current_time(self):
        return datetime.now().strftime("%H:%M:%S")
    
    def get_chat_history(self):
        """Extract conversation history from chat_display."""
        history = [{"role": "system", "content": self.gui.config.system_prompt.get()}]
        chat_content = self.gui.chat_display.get(1.0, tk.END).strip()
        if not chat_content:
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
        return history

    def process_request(self, user_text):
        print("Starting process_request")
        try:
            api_key = self.gui.config.get_api_key()
            base_url = self.gui.config.get_base_url()
            if not api_key or not base_url:
                raise ValueError("Invalid API key or base URL for selected model")
            client = OpenAI(api_key=api_key, base_url=base_url)
            messages = self.get_chat_history()
            if user_text.strip():
                messages.append({"role": "user", "content": user_text})
            self.gui.input_tokens = sum(len(m["content"].split()) for m in messages)
            self.gui.stream_start_time = time.time()
            response = client.chat.completions.create(
                model=self.gui.config.model.get(),
                messages=messages,
                stream=self.gui.config.streaming.get(),
                max_tokens=8096
            )
            print("API call successful, handling response")
            self.handle_response(response)
        except Exception as e:
            print(f"Error in process_request: {str(e)}")
            self.gui.show_error(f"API Error: {str(e)}")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")
            return
        finally:
            print("Executing finally block in process_request")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")

    def handle_response(self, response):
        print("Starting handle_response")
        print(f"parse_and_display_content available: {hasattr(self, 'parse_and_display_content')}")
        self.gui.current_response = ""
        self.gui.update_display("\n> ", "assistant")
        try:
            if self.gui.config.streaming.get():
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    self.gui.current_response += content
                    self.parse_and_display_content(content)
                # Tokens counted post-stream (approximate)
                self.gui.output_tokens = len(self.gui.current_response.split())
            else:
                full_response = response.choices[0].message.content
                self.gui.current_response = full_response
                self.parse_and_display_content(full_response)
                self.gui.output_tokens = len(full_response.split())
            self.gui.update_status()
            print("Completed handle_response successfully")
        except Exception as e:
            print(f"Error in handle_response: {str(e)}")
            self.gui.show_error(f"Response Error: {str(e)}")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")
            raise

    def parse_and_display_content(self, content):
        print("Entering parse_and_display_content")  # Debug print
        self.gui.code_parse_buffer += content
        while True:
            if self.gui.in_code_block:
                end_idx = self.gui.code_parse_buffer.find('```')
                if end_idx == -1:
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer, "code")
                    self.gui.code_parse_buffer = ""
                    break
                else:
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer[:end_idx], "code")
                    self.gui.code_parse_buffer = self.gui.code_parse_buffer[end_idx+3:]
                    self.gui.in_code_block = False
            else:
                start_idx = self.gui.code_parse_buffer.find('```')
                if start_idx == -1:
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer, "assistant")
                    self.gui.code_parse_buffer = ""
                    break
                else:
                    self.gui.root.after(0, self.gui.update_display, self.gui.code_parse_buffer[:start_idx], "assistant")
                    self.gui.code_parse_buffer = self.gui.code_parse_buffer[start_idx+3:]
                    self.gui.in_code_block = True
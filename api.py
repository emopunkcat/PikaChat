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

    def process_request(self, user_text):
        print("Starting process_request")  # Debug print
        try:
            self.client = OpenAI(api_key=self.gui.config.get_api_key(), base_url=self.gui.config.get_base_url())
            self.gui.messages = [
                {"role": "system", "content": self.gui.config.system_prompt.get()}
            ] if self.gui.config.system_prompt.get() else []
            self.gui.messages.append({"role": "user", "content": user_text})

            self.gui.stream_start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.gui.config.model.get(),
                messages=self.gui.messages,
                stream=self.gui.config.streaming.get(),
                max_tokens=8096
            )

            print("API call successful, handling response")  # Debug print
            self.handle_response(response)

        except Exception as e:
            print(f"Error in process_request: {str(e)}")  # Debug print
            self.gui.show_error(f"API Error: {str(e)}")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")  # Updated method call
            return  # Stop further processing
        finally:
            print("Executing finally block in process_request")  # Debug print
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")  # Updated method call

    def handle_response(self, response):
        print("Starting handle_response")  # Debug print
        print(f"parse_and_display_content available: {hasattr(self, 'parse_and_display_content')}")  # Debug print
        self.gui.current_response = ""
        self.gui.update_display("\n> ", "assistant")

        try:
            if self.gui.config.streaming.get():
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    self.gui.current_response += content
                    self.parse_and_display_content(content)

                    if hasattr(chunk, 'usage') and chunk.usage:
                        self.gui.input_tokens += chunk.usage.prompt_tokens
                        self.gui.output_tokens += chunk.usage.completion_tokens
            else:
                full_response = response.choices[0].message.content
                self.parse_and_display_content(full_response)
                self.gui.current_response = full_response

                if response.usage:
                    self.gui.input_tokens += response.usage.prompt_tokens
                    self.gui.output_tokens += response.usage.completion_tokens

            self.gui.messages.append({"role": "assistant", "content": self.gui.current_response})
            self.gui.update_status()
            print("Completed handle_response successfully")  # Debug print

        except Exception as e:
            print(f"Error in handle_response: {str(e)}")  # Debug print
            self.gui.show_error(f"Response Error: {str(e)}")
            self.gui.active_request = False
            self.gui.manage_thinking_animation("stop")  # Updated method call
            raise  # Re-raise to trigger finally block in process_request

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
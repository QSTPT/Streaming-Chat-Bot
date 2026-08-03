from __future__ import annotations

import asyncio
import json
import os
from http import cookiejar
from typing import Any
from urllib import error, parse, request

import flet as ft
import websockets

COOKIE_NAME = "historia_session"
DEFAULT_BASE_URL = os.getenv("CHAT_BOT_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_WS_PATH = "/ws/current_chat"


def build_api_url(base_url: str, path: str) -> str:
    return parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def build_websocket_url(base_url: str, path: str = DEFAULT_WS_PATH) -> str:
    parsed = parse.urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}{path}"


def build_cookie_header(cookie_name: str, cookie_value: str) -> str:
    return f"{cookie_name}={cookie_value}"


def authenticate(base_url: str, endpoint: str, username: str, password: str, name: str = "") -> tuple[str, str]:
    api_url = build_api_url(base_url, endpoint)
    if endpoint == "/signup":
        payload = json.dumps({"name": name, "username": username, "password": password}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
    else:
        payload = parse.urlencode({"username": username, "password": password}).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
    req = request.Request(
        api_url, 
        data=payload,
        headers=headers, 
        method="POST"
    )

    jar = cookiejar.CookieJar()
    opener = request.build_opener(request.HTTPCookieProcessor(jar))

    try:
        with opener.open(req, timeout=10) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(body or f"Request failed with status {exc.code}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the backend at {api_url}: {exc.reason}") from exc

    for cookie in jar:
        if cookie.name == COOKIE_NAME:
            return cookie.value, body
        
    if endpoint == "/signup":
        return "", body

    raise RuntimeError("Success, but no session cookie was returned by the server.")


class ChatApp(ft.Container):
    def __init__(self):
        super().__init__(expand=True, padding=12)
        
        self.base_url = os.getenv("CHAT_BOT_BASE_URL", DEFAULT_BASE_URL)
        self.session_cookie: str | None = None
        self.websocket: Any | None = None
        
        self.stream_active = False
        self.stream_content = ""
        self.stream_text_control: ft.Text | None = None
        self.stream_container: ft.Row | None = None
        
        # --- Screen Elements: Authentication ---
        self.is_login_mode = True 
        
        self.auth_title = ft.Text("Welcome Back", size=32, weight=ft.FontWeight.BOLD)
        self.auth_subtitle = ft.Text("Sign in to start chatting.", color=ft.Colors.BLUE_GREY_300)
        self.name_field = ft.TextField(label="Full Name", width=320, border_radius=8, visible=False)
        self.username_field = ft.TextField(label="Username", width=320, border_radius=8)
        self.password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, width=320, border_radius=8)
        self.auth_error_text = ft.Text("", color=ft.Colors.RED_400)
        self.auth_button = ft.Button("Login", on_click=self.handle_auth, width=320, height=45)
        self.toggle_auth_button = ft.TextButton("Don't have an account? Sign up here", on_click=self.toggle_auth_mode)
        
        # --- Screen Elements: Chat ---
        self.status_text = ft.Text("Ready to connect", size=12, color=ft.Colors.BLUE_GREY_300)
        self.token_status = ft.Text("Tokens: 0 / 0", size=12)
        self.reconnect_button = ft.TextButton("Reconnect", on_click=self.handle_reconnect, visible=False)
        self.stop_button = ft.Button("Stop generating", on_click=self.handle_stop, visible=False, bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE)
        self.history_view = ft.ListView(expand=True, spacing=10, padding=10, auto_scroll=True)
        self.message_field = ft.TextField(label="Type a message...", expand=True, on_submit=self.handle_send_message, border_radius=20)
        
        self.content = self.build_auth_view()

    # --- Screen Builders ---
    def build_auth_view(self) -> ft.Container:
        form_column = ft.Column(
            [
                self.auth_title,
                self.auth_subtitle,
                ft.Container(height=10),
                self.name_field,
                self.username_field,
                self.password_field,
                ft.Container(height=10),
                self.auth_button,
                self.toggle_auth_button,
                self.auth_error_text,
                self.status_text,
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=form_column,
                    padding=40,
                    width=420,
                ),
                elevation=8,
                shape=ft.RoundedRectangleBorder(radius=16),
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    def build_chat_view(self) -> ft.Column:
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("AI Chat", size=24, weight=ft.FontWeight.BOLD),
                        self.reconnect_button,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=ft.Colors.BLUE_GREY_800),
                self.history_view,
                ft.Row(
                    [
                        self.message_field,
                        ft.IconButton(icon=ft.Icons.SEND, on_click=self.handle_send_message, icon_color=ft.Colors.BLUE_400),
                        self.stop_button,
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Container(
                            content=self.token_status,
                            padding=ft.padding.only(left=12, right=12, top=6, bottom=6),
                            border=ft.border.all(1, ft.Colors.BLUE_GREY_800),
                            border_radius=20,
                            bgcolor=ft.Colors.BLUE_GREY_900,
                        ),
                        self.status_text,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            ],
            expand=True,
        )

    # --- Screen Switching & UI Updates ---
    def show_auth_view(self) -> None:
        self.content = self.build_auth_view()
        self.update()

    def show_chat_view(self) -> None:
        self.content = self.build_chat_view()
        self.update()

    def toggle_auth_mode(self, event: ft.ControlEvent) -> None:
        self.is_login_mode = not self.is_login_mode
        self.auth_error_text.value = ""
        
        if self.is_login_mode:
            self.auth_title.value = "Welcome Back"
            self.auth_subtitle.value = "Sign in to start chatting."
            self.auth_button.text = "Login"
            self.toggle_auth_button.text = "Don't have an account? Sign up here"
            self.name_field.visible = False
        else:
            self.auth_title.value = "Create Account"
            self.auth_subtitle.value = "Sign up to start your journey."
            self.auth_button.text = "Sign Up"
            self.toggle_auth_button.text = "Already have an account? Log in here"
            self.name_field.visible = True
            
        self.update()

    def set_status(self, message: str) -> None:
        self.status_text.value = message
        self.update()

    def clear_error(self) -> None:
        self.auth_error_text.value = ""
        self.update()

    def create_message_bubble(self, role: str, content: str) -> ft.Row:
        is_user = role == "user"
        
        bubble = ft.Container(
            content=ft.Text(content, selectable=True),
            padding=ft.padding.only(left=16, right=16, top=12, bottom=12),
            border_radius=16,
            bgcolor=ft.Colors.BLUE_800 if is_user else ft.Colors.BLUE_GREY_900,
            alignment=ft.Alignment(-1, 0),
            margin=ft.margin.only(top=4, bottom=4),
            width=600, 
            animate=ft.animation.Animation(200, "decelerate"),
        )
        
        return ft.Row(
            [bubble],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
        )

    # --- Chat Features ---
    def append_history(self, history: list[dict[str, Any]]) -> None:
        self.history_view.controls.clear()
        for message in history:
            content = str(message.get("content", ""))
            role = str(message.get("role", "assistant"))
            self.history_view.controls.append(self.create_message_bubble(role, content))
        self.update()

    def append_user_message(self, content: str) -> None:
        self.history_view.controls.append(self.create_message_bubble("user", content))
        self.update()

    def start_stream_message(self) -> None:
        self.stream_active = True
        self.stop_button.visible = True
        self.stream_content = ""
        self.stream_text_control = ft.Text("", selectable=True)
        
        bubble = ft.Container(
            content=self.stream_text_control,
            padding=ft.padding.only(left=16, right=16, top=12, bottom=12),
            border_radius=16,
            bgcolor=ft.Colors.BLUE_GREY_900,
            alignment=ft.Alignment(-1, 0),
            margin=ft.margin.only(top=4, bottom=4),
            width=600,
        )
        
        self.stream_container = ft.Row([bubble], alignment=ft.MainAxisAlignment.START)
        self.history_view.controls.append(self.stream_container)
        self.update()

    def append_stream_token(self, content: str) -> None:
        if not self.stream_active:
            self.start_stream_message()
        self.stream_content += content
        if self.stream_text_control is not None:
            self.stream_text_control.value = self.stream_content
            self.stream_text_control.update() 

    def finish_stream(self) -> None:
        self.stream_active = False
        self.stop_button.visible = False
        self.stream_content = ""
        self.stream_text_control = None
        self.stream_container = None
        self.update()

    def update_token_status(self, payload: dict[str, Any]) -> None:
        self.token_status.value = (
            f"Prompt: {payload.get('prompt_tokens', 0)} | Assistant: {payload.get('assistant_tokens', 0)} | "
            f"Total: {payload.get('total_session_tokens', 0)} / {payload.get('max_context', 0)}"
        )
        self.update()

    # --- Actions ---
    async def handle_auth(self, event: ft.ControlEvent) -> None:
        name = self.name_field.value.strip()
        username = self.username_field.value.strip()
        password = self.password_field.value.strip()
        
        if not self.is_login_mode and not name:
            self.auth_error_text.value = "Please enter your Name."
            self.update()
            return
        
        if not username or not password:
            self.auth_error_text.value = "Please enter both a username and a password."
            self.update()
            return

        self.clear_error()
        self.set_status("Connecting...")
        
        endpoint = "/login" if self.is_login_mode else "/signup"
        
        try:
            if not self.is_login_mode:
                await asyncio.to_thread(
                authenticate, self.base_url, "/signup", username, password, name
            )
                self.set_status("Account created! Logging in...")
                
            self.session_cookie, _ = await asyncio.to_thread(
            authenticate, self.base_url, "/login", username, password, name
            )
            
            self.show_chat_view()
            self.set_status("Connected. Waiting for chat history...")
            await self.connect_websocket()
            
        except Exception as exc:
            self.auth_error_text.value = str(exc)
            self.show_auth_view()
            self.set_status("Request failed")

    async def connect_websocket(self) -> None:
        if not self.session_cookie:
            return
        ws_url = build_websocket_url(self.base_url, DEFAULT_WS_PATH)
        headers = {"Cookie": build_cookie_header(COOKIE_NAME, self.session_cookie)}
        try:
            self.websocket = await websockets.connect(ws_url, extra_headers=headers, ping_interval=None)
            self.reconnect_button.visible = False
            self.set_status("Connected to the chat stream")
            asyncio.create_task(self.listen_for_messages())
        except Exception as exc: 
            self.reconnect_button.visible = True
            self.set_status(f"Connection error: {exc}")
            self.update()

    async def listen_for_messages(self) -> None:
        if not self.websocket:
            return
        try:
            async for raw_message in self.websocket:
                payload = json.loads(raw_message)
                message_type = payload.get("type")
                if message_type == "history":
                    self.append_history(payload.get("data", []))
                elif message_type == "token":
                    self.append_stream_token(payload.get("content", ""))
                elif message_type in {"end", "stopped"}:
                    self.finish_stream()
                elif message_type == "token_update":
                    self.update_token_status(payload)
        except websockets.ConnectionClosed:
            self.reconnect_button.visible = True
            self.set_status("The connection dropped. Reconnect to continue chatting.")
            self.update()
        except Exception as exc: 
            self.reconnect_button.visible = True
            self.set_status(f"Stream error: {exc}")
            self.update()

    async def handle_send_message(self, event: ft.ControlEvent | None = None) -> None:
        message = self.message_field.value.strip()
        if not message:
            return
        self.message_field.value = ""
        self.append_user_message(message)

        if self.websocket is None:
            self.set_status("Not connected yet; please log in again.")
            return

        try:
            await self.websocket.send(json.dumps({"action": "message", "content": message}))
            self.set_status("Message sent. Waiting for the bot to respond...")
        except Exception as exc: 
            self.set_status(f"Unable to send message: {exc}")

    async def handle_stop(self, event: ft.ControlEvent) -> None:
        if self.websocket is not None:
            try:
                await self.websocket.send(json.dumps({"action": "stop"}))
            except Exception as exc: 
                self.set_status(f"Unable to stop the stream: {exc}")
        self.finish_stream()
        self.set_status("Streaming stopped.")

    async def handle_reconnect(self, event: ft.ControlEvent) -> None:
        self.reconnect_button.visible = False
        self.update()
        await self.connect_websocket()


def main(page: ft.Page) -> None:
    page.title = "AI Chat Bot"
    page.window_width = 1000
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    
    page.add(ChatApp())
    page.update()


def run_app() -> None:
    ft.run(main)


if __name__ == "__main__":
    run_app()
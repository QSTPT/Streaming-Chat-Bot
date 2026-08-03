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


def authenticate(base_url: str, username: str, password: str) -> tuple[str, str]:
    api_url = build_api_url(base_url, "/login")
    payload = parse.urlencode({"username": username, "password": password}).encode("utf-8")
    req = request.Request(api_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")

    jar = cookiejar.CookieJar()
    opener = request.build_opener(request.HTTPCookieProcessor(jar))

    try:
        with opener.open(req, timeout=10) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(body or f"Authentication failed with status {exc.code}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the backend at {api_url}: {exc.reason}") from exc

    for cookie in jar:
        if cookie.name == COOKIE_NAME:
            return cookie.value, body

    raise RuntimeError("Login succeeded, but no session cookie was returned by the server")


class ChatApp(ft.BaseControl):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.base_url = os.getenv("CHAT_BOT_BASE_URL", DEFAULT_BASE_URL)
        self.session_cookie: str | None = None
        self.websocket: Any | None = None
        self.stream_active = False
        self.stream_content = ""
        self.stream_text_control: ft.Text | None = None
        self.stream_container: ft.Container | None = None
        self.status_text = ft.Text("Ready to connect")
        self.token_status = ft.Text("Tokens: 0 / 0")
        self.reconnect_button = ft.TextButton("Reconnect", on_click=self.handle_reconnect, visible=False)
        self.stop_button = ft.ElevatedButton("Stop generating", on_click=self.handle_stop, visible=False)
        self.history_view = ft.ListView(expand=True, spacing=10, padding=10, auto_scroll=True)
        self.username_field = ft.TextField(label="Username", width=280)
        self.password_field = ft.TextField(label="Password", password=True, width=280)
        self.message_field = ft.TextField(label="Type a message", expand=True, on_submit=self.handle_send_message)
        self.login_error_text = ft.Text("", color=ft.colors.RED_400)
        self.view_container = ft.Container(expand=True, padding=12, content=self.build_login_view())

    def build(self) -> ft.Container:
        return self.view_container

    def build_login_view(self) -> ft.Column:
        return ft.Column(
            [
                ft.Text("Welcome back", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Sign in to start chatting with the local streaming bot.", color=ft.colors.BLUE_GREY_300),
                ft.Divider(),
                self.username_field,
                self.password_field,
                ft.ElevatedButton("Login", on_click=self.handle_login),
                self.login_error_text,
                self.status_text,
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=420,
        )

    def build_chat_view(self) -> ft.Column:
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Streaming Chat", size=24, weight=ft.FontWeight.BOLD),
                        self.reconnect_button,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.history_view,
                ft.Row(
                    [
                        self.message_field,
                        ft.ElevatedButton("Send", on_click=self.handle_send_message),
                        self.stop_button,
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=self.token_status,
                    padding=8,
                    border=ft.border.all(1, ft.colors.BLUE_GREY_700),
                    border_radius=8,
                    bgcolor=ft.colors.BLUE_GREY_900,
                ),
                self.status_text,
            ],
            expand=True,
        )

    def show_login_view(self) -> None:
        self.view_container.content = self.build_login_view()
        self.page.update()

    def show_chat_view(self) -> None:
        self.view_container.content = self.build_chat_view()
        self.page.update()

    def set_status(self, message: str) -> None:
        self.status_text.value = message
        self.page.update()

    def clear_error(self) -> None:
        self.login_error_text.value = ""
        self.page.update()

    def create_message_bubble(self, role: str, content: str) -> ft.Container:
        is_user = role == "user"
        bubble = ft.Container(
            content=ft.Text(content, selectable=True, max_lines=40),
            padding=12,
            border_radius=12,
            bgcolor=ft.colors.BLUE_600 if is_user else ft.colors.GREY_900,
            alignment=ft.alignment.center_left,
            margin=ft.margin.only(top=4, bottom=4),
            width=420,
            animate=ft.animation.Animation(200, "decelerate"),
        )
        if is_user:
            bubble.alignment = ft.alignment.center_right
        return bubble

    def append_history(self, history: list[dict[str, Any]]) -> None:
        self.history_view.controls.clear()
        for message in history:
            content = str(message.get("content", ""))
            role = str(message.get("role", "assistant"))
            self.history_view.controls.append(self.create_message_bubble(role, content))
        self.page.update()

    def append_user_message(self, content: str) -> None:
        self.history_view.controls.append(self.create_message_bubble("user", content))
        self.page.update()

    def start_stream_message(self) -> None:
        self.stream_active = True
        self.stop_button.visible = True
        self.stream_content = ""
        self.stream_text_control = ft.Text("", selectable=True, max_lines=40)
        self.stream_container = ft.Container(
            content=self.stream_text_control,
            padding=12,
            border_radius=12,
            bgcolor=ft.colors.GREY_900,
            alignment=ft.alignment.center_left,
            margin=ft.margin.only(top=4, bottom=4),
            width=420,
        )
        self.history_view.controls.append(self.stream_container)
        self.page.update()

    def append_stream_token(self, content: str) -> None:
        if not self.stream_active:
            self.start_stream_message()
        self.stream_content += content
        if self.stream_text_control is not None:
            self.stream_text_control.value = self.stream_content
            self.page.update()

    def finish_stream(self) -> None:
        self.stream_active = False
        self.stop_button.visible = False
        self.stream_content = ""
        self.stream_text_control = None
        self.stream_container = None
        self.page.update()

    def update_token_status(self, payload: dict[str, Any]) -> None:
        self.token_status.value = (
            f"Prompt: {payload.get('prompt_tokens', 0)} | Assistant: {payload.get('assistant_tokens', 0)} | "
            f"Total: {payload.get('total_session_tokens', 0)} / {payload.get('max_context', 0)}"
        )
        self.page.update()

    async def handle_login(self, event: ft.ControlEvent) -> None:
        username = self.username_field.value.strip()
        password = self.password_field.value.strip()
        if not username or not password:
            self.login_error_text.value = "Please enter both username and password."
            self.page.update()
            return

        self.clear_error()
        self.set_status("Signing in...")
        try:
            self.session_cookie, _ = await asyncio.to_thread(authenticate, self.base_url, username, password)
            self.show_chat_view()
            self.set_status("Connected. Waiting for the chat history...")
            await self.connect_websocket()
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.login_error_text.value = str(exc)
            self.show_login_view()
            self.set_status("Login failed")

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
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.reconnect_button.visible = True
            self.set_status(f"Connection error: {exc}")

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
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.reconnect_button.visible = True
            self.set_status(f"Stream error: {exc}")

    async def handle_send_message(self, event: ft.ControlEvent | None = None) -> None:
        message = self.message_field.value.strip()
        if not message:
            return
        self.message_field.value = ""
        self.append_user_message(message)
        self.page.update()

        if self.websocket is None:
            self.set_status("Not connected yet; please log in again.")
            return

        try:
            await self.websocket.send(json.dumps({"action": "message", "content": message}))
            self.set_status("Message sent. Waiting for the assistant response...")
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.set_status(f"Unable to send message: {exc}")

    async def handle_stop(self, event: ft.ControlEvent) -> None:
        if self.websocket is not None:
            try:
                await self.websocket.send(json.dumps({"action": "stop"}))
            except Exception as exc:  # pragma: no cover - UI feedback path
                self.set_status(f"Unable to stop the stream: {exc}")
        self.finish_stream()
        self.set_status("Streaming stopped.")

    async def handle_reconnect(self, event: ft.ControlEvent) -> None:
        self.reconnect_button.visible = False
        self.page.update()
        await self.connect_websocket()


def main(page: ft.Page) -> None:
    page.title = "Streaming Chat Bot"
    page.window_width = 1000
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.add(ChatApp(page))
    page.update()


def run_app() -> None:
    ft.app(target=main)


if __name__ == "__main__":
    run_app()

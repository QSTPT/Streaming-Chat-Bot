from app.ui.flet_app import build_api_url, build_cookie_header, build_websocket_url


def test_build_api_url_joins_paths() -> None:
    assert build_api_url("http://127.0.0.1:8000", "/login") == "http://127.0.0.1:8000/login"


def test_build_websocket_url_uses_ws_scheme() -> None:
    assert build_websocket_url("http://127.0.0.1:8000") == "ws://127.0.0.1:8000/ws/current_chat"


def test_build_cookie_header_formats_cookie() -> None:
    assert build_cookie_header("historia_session", "abc123") == "historia_session=abc123"

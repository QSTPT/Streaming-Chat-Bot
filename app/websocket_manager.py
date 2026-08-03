from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections.get(user_id, set()).discard(websocket)

    async def send_message(self, message: str | dict, websocket: WebSocket):
        if isinstance(message, dict):
            await websocket.send_json(message)
        else:
            await websocket.send_text(message)

    async def receive_json_message(self, websocket: WebSocket):
        return await websocket.receive_json()

    async def receive_text(self, websocket: WebSocket):
        return await websocket.receive_text()


manager = ConnectionManager()
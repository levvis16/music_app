from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

class ConnectionManager():
    def __init__(self):
        self.active_rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, venue_id: int):
        await websocket.accept()
        if venue_id not in self.active_rooms:
            self.active_rooms[venue_id] = set()

        self.active_rooms[venue_id].add(websocket)

    def disconnect(self, websocket: WebSocket, venue_id: int):
        if venue_id in self.active_rooms:
            self.active_rooms[venue_id].discard(websocket)
            if not self.active_rooms[venue_id]:
                del self.active_rooms[venue_id]

    async def broadcast(self, venue_id: int, event: str, data: dict):
        if venue_id not in self.active_rooms:
            return

        message = json.dumps({"event":event, "data":data})
        for client in self.active_rooms[venue_id].copy():
            try:
                await client.send_text(message)
            except:
                await self.disconnect(client, venue_id)

manager = ConnectionManager()
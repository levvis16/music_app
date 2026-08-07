from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect

from app.api.v1.routers.router_queue import router as queue_router
from app.api.v1.routers.router_track import router as track_router
from app.api.v1.routers.router_venue import router as venue_router
#from app.api.v1.routers.router_black_list import router as black_list_router
#from app.api.v1.routers.router_white_list import router as white_list_router
#from app.api.v1.routers.router_statistics import router as statistics_router
from app.websocket.websocket import manager

app = FastAPI(
    title = "DJ service",
    description="сервис для заказа музыки за донат",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(venue_router)
app.include_router(queue_router)
app.include_router(track_router)
#app.include_router(black_list_router)
#app.include_router(white_list_router)
#app.include_router(statistics_router)

@app.get('/')
async def root():
    return {"message": "DJ service API", "status": "running"}

@app.websocket("/ws/{venue_id}")
async def websocket_endpoint(websocket: WebSocket, venue_id: str):
    await manager.connect(websocket, venue_id)
    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket, venue_id)
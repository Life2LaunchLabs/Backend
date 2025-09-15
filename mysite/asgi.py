import os
from starlette.applications import Starlette
from starlette.websockets import WebSocket
import uvicorn

app = Starlette()

@app.websocket_route("/ws/test")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("hello")
    await websocket.close()

# Export as 'application' for Django/Railway compatibility
application = app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
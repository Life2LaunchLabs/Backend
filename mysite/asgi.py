import os
from channels.routing import ProtocolTypeRouter
from channels.generic.websocket import AsyncWebsocketConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

class Echo(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send("ok")

application = ProtocolTypeRouter({
    "http": lambda scope: None,  # ignore http
    "websocket": Echo.as_asgi(),
})
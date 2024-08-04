import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DeployLogsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.deployment_uuid = self.scope['url_route']['kwargs']['uuid']
        self.group_name = f'deployment_{self.deployment_uuid}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'deploy_logs',
                'data': data,
            }
        )

    async def deploy_logs(self, event):
        await self.send(text_data=json.dumps(event['data']))

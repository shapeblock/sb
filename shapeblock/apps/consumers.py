import json

from shapeblock.apps.models import App

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

import threading
from kubernetes import client, config, watch


class AppStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'apps'

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
                'type': 'app_status_message',
                'data': data
            }
        )

    async def app_status_message(self, event):
        await self.send(text_data=json.dumps(event['data']))


class PodLogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.app_uuid = self.scope["url_route"]["kwargs"]["app_uuid"]
        self.channel_layer = get_channel_layer()

        # Accept the WebSocket connection
        await self.accept()

        # Load kubeconfig and set up Kubernetes client
        self.namespace = await self.get_app_details()
        config.load_incluster_config()

        # Start streaming logs in a separate thread
        thread = threading.Thread(target=self.stream_logs)
        thread.start()

    def stream_logs(self):
        v1 = client.CoreV1Api()
        w = watch.Watch()

        pods = v1.list_namespaced_pod(namespace=self.namespace, label_selector=f"appUuid={self.app_uuid}")
        pod = pods.items[0]
        self.pod_name = pod.metadata.name
        for line in w.stream(
            v1.read_namespaced_pod_log, name=self.pod_name, namespace=self.namespace, since_seconds=300
        ):
            formatted_line = f"{line}\n"
            # Send message to the channel layer from the thread
            async_to_sync(self.channel_layer.send)(
                self.channel_name, {"type": "websocket.send", "text": json.dumps({"message": formatted_line})}
            )

    async def disconnect(self, close_code):
        # Handle disconnection
        pass

    @database_sync_to_async
    def get_app_details(self):
        app = App.objects.get(uuid=self.app_uuid)
        return app.project.name

    async def websocket_send(self, event):
        # Send the message to the WebSocket
        await self.send(text_data=event["text"])

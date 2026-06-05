import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect('ws://127.0.0.1:5173/ws') as ws:
            print('Connected!')
            for i in range(2):
                msg = await ws.recv()
                print(f'Received message length: {len(msg)}')
                data = json.loads(msg)
                print(f'Type: {data.get("type")}')
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())

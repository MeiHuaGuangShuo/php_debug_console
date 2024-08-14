import asyncio
from aiohttp import web
from loguru import logger
from rich.pretty import pretty_repr
from typing import List
from concurrent.futures import ThreadPoolExecutor

auth = "debug_console_auth"
full_key_check = False
logs: List[dict] = []
websockets_list: List[web.WebSocketResponse] = []
INTRODUCE_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>WebSocket转发工具</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      text-align: center;
      padding: 50px;
    }
    h1 {
      font-size: 28px;
      margin-bottom: 20px;
    }
    p {
      font-size: 18px;
      margin-bottom: 10px;
    }
  </style>
</head>
<body>
  <h1><a href="https://github.com/MeiHuaGuangShuo/php_debug_console">WebSocket转发工具</a></h1>
  <p>转发服务端</p>
</body>
</html>
"""


async def handle_websocket(request: web.Request):
    global websockets_list
    request_headers = dict(request.headers)
    ticket = request.query.get('auth', '')
    if not request_headers:
        return web.json_response({"success": False, "reason": "Headers does not valid"}, status=400)
    if ("http" in request_headers.get("User-Agent", '') or "Mozilla" in request_headers.get("User-Agent",
                                                                                            '')) and not ticket:
        return web.Response(text=INTRODUCE_HTML, content_type='text/html')
    clientIp = request_headers.get("CF-Connecting-IP", request.remote)
    logger.info(f"Connect Request from {clientIp}")
    if ticket != auth:
        logger.warning(f"{clientIp} Authentication failed. Headers: {dict(request_headers)} Ticket: {ticket}")
        return web.Response(status=400)
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    logger.info(f"{clientIp} Connected.")
    websockets_list.append(websocket)
    try:
        async for message in websocket:
            try:
                pass
            except Exception as err:
                logger.error(
                    f'Invalid Response.\n{err.__class__.__name__}: {err}\nClient: {clientIp}\nMessage:\n>{pretty_repr(message)}')
                await websocket.close(code=1008, message=b'Invalid Response.')
                break
            else:
                logger.info(f"{clientIp} -> [{message.get('code', 'Error')}]")
    except Exception as err:
        logger.error(f'{clientIp} -> [bold red]{err.__class__.__name__}[/]: [white bold]{err}[/]')
    websockets_list.remove(websocket)
    logger.info(f"{clientIp} Disconnected.")


async def send_log(mes):
    for ws in websockets_list:
        try:
            if ws.closed:
                websockets_list.remove(ws)
                continue
            await ws.send_json(mes)
        except Exception as err:
            logger.error(f'Send log error.\n{err.__class__.__name__}: {err}')
            try:
                await ws.close(code=1008)
            except Exception as err:
                logger.error(f'Close ws error.\n{err.__class__.__name__}: {err}')
            finally:
                websockets_list.remove(ws)


async def receive_log(request: web.Request):
    data = await request.json()
    if full_key_check:
        for k in ['timestamp', 'file', 'function', 'line_no', 'level', 'message']:
            if k not in data:
                return web.Response(status=400)
    loop.create_task(send_log(data))
    return web.Response(status=200)


async def main():
    app = web.Application()
    app.add_routes([web.get('/ws', handle_websocket), web.post('/log', receive_log)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 60721)
    await site.start()
    logger.info('Server started.')
    await asyncio.gather(*asyncio.all_tasks())


if __name__ == '__main__':
    with ThreadPoolExecutor() as pool:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

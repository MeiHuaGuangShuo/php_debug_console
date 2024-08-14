import asyncio
import datetime
import json
import time
import inspect
from loguru import logger
from urllib.parse import quote_plus
import websockets
import base64
import sys

ws_url = "ws://localhost:60721/ws"
auth = "debug_console_auth"

logger.remove()
logger.add(sys.stdout,
           format="{message}",
           enqueue=True, level=0)
requestUserAgent = f"PHP Debug Console (WS) v1.0 (+https://github.com/MeiHuaGuangShuo/php_debug_console)"


class _slogger:

    def __init__(self):
        pass

    def send_log(self, level, message):
        curr_frame = inspect.currentframe()
        caller_frame = inspect.getouterframes(curr_frame, 3)
        caller_file = caller_frame[2][1]
        caller_function = caller_frame[2][3]
        caller_line_no = caller_frame[2][2]
        data = {
            "level"    : level,
            "timestamp": time.time(),
            "file"     : caller_file,
            "function" : caller_function,
            "line_no"  : caller_line_no,
            "message"  : base64.b64encode(message.encode()).decode()
        }
        asyncio.create_task(output_info(data))

    def trace(self, message):
        self.send_log('TRACE', str(message))

    def debug(self, message):
        self.send_log('DEBUG', str(message))

    def info(self, message):
        self.send_log('INFO', str(message))

    def warning(self, message):
        self.send_log('WARNING', str(message))

    def success(self, message):
        self.send_log('SUCCESS', str(message))

    def error(self, message):
        self.send_log('ERROR', str(message))

    def critical(self, message):
        self.send_log('CRITICAL', str(message))


slogger = _slogger()


async def output_info(data: dict):
    level = data.get("level")
    if level not in ["TRACE", "DEBUG", "INFO", "WARNING", "SUCCESS", "ERROR", "CRITICAL"]:
        logger.error("Invalid log level")
        return
    timestamp = data.get("timestamp", time.time())
    if isinstance(timestamp, str):
        log_time = timestamp
        if timestamp.isnumeric():
            timestamp = int(timestamp)
            if len(str(timestamp)) > 10:
                timestamp = int(timestamp) / 1000
            log_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
        elif timestamp.replace('.', '').isnumeric():
            timestamp = float(timestamp)
            log_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
    else:
        if not isinstance(timestamp, (int, float)):
            slogger.error("Invalid timestamp")
            slogger.info(type(timestamp))
            return
        if not isinstance(timestamp, float):
            if len(str(timestamp)) > 10:
                data["timestamp"] = timestamp / 1000
        log_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    message = (f"<green>{log_time}</green> <red>|</red> "
               f"<level>{level: <8}</level><red>|</red> <level>"
               f"{data.get('file')}:{data.get('function')}:{data.get('line_no')} - "
               f"{base64.b64decode(data.get('message')).decode().replace('<', '\\<').replace('>', '\\>')}</level>")
    logger.opt(colors=True).log(level, message)


async def main():
    while True:
        uri = '%s?auth=%s' % (ws_url, quote_plus(auth))
        headers = {'User-Agent': requestUserAgent}
        try:
            async with websockets.connect(uri, extra_headers=headers) as websocket:
                slogger.info(f"Websocket connected")
                try:
                    async for raw_message in websocket:
                        json_message = json.loads(raw_message)
                        await output_info(json_message)
                except asyncio.CancelledError:
                    slogger.warning(f"Closing the websocket connections...")
                    await websocket.close()
                    break
                except Exception as err:
                    logger.exception(err)
                    slogger.warning(f"The stream connection will be reconnected after 5 seconds")
                    await asyncio.sleep(5)
        except Exception as err:
            logger.exception(err)
            slogger.warning(f"The stream connection will be reconnected after 5 seconds")
            await asyncio.sleep(5)

    slogger.info(f"Stream connection was stopped.")


if __name__ == '__main__':
    asyncio.run(main())

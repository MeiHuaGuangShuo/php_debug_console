from aiohttp import web
from loguru import logger
import base64
import sys

logger.remove()
logger.add(sys.stdout,
           format="<green>{time:MM-DD HH:mm:ss:SSS}</green> <red>|</red> <level>{level: <8}</level> "
                  "<red>|</red> <level>{message}</level>",
           enqueue=True, level=0)


async def output_info(request: web.Request):
    data = await request.json()
    level = data.get("level")
    if level not in ["TRACE", "DEBUG", "INFO", "WARNING", "SUCCESS", "ERROR", "CRITICAL"]:
        logger.error("Invalid log level")
        return web.json_response({"error": "Invalid log level"})
    message = (f"{data.get('file')}:{data.get('function')}:{data.get('line_no')} - "
               f"{base64.b64decode(data.get('message')).decode()}")
    logger.log(level, message)
    return web.json_response(data)


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.post('/log', output_info)])
    web.run_app(app, port=60721)

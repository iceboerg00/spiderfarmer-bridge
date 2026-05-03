import asyncio
import logging
import signal
import sys

import paho.mqtt.client as mqtt

from proxy.config import load_config
from proxy.mitm_proxy import MITMProxy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config("config/config.yaml")
    mqcfg = config["mosquitto"]

    mq = mqtt.Client(client_id="sf-bridge-proxy")
    mq.connect(mqcfg["host"], mqcfg["port"], keepalive=60)
    mq.loop_start()

    proxy = MITMProxy(config, mq, config_path="config/config.yaml")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def on_command(client, userdata, message):
        asyncio.run_coroutine_threadsafe(
            proxy.handle_command(message.topic, message.payload.decode()),
            loop,
        )

    mq.subscribe("spiderfarmer/+/command/#")
    mq.on_message = on_command

    server_ssl_ctx = proxy.build_server_ssl_ctx()
    pcfg = config["proxy"]

    async def run() -> None:
        server = await asyncio.start_server(
            proxy.handle_client,
            host=pcfg["listen_host"],
            port=pcfg["listen_port"],
            ssl=server_ssl_ctx,
        )
        stop = asyncio.Event()
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, stop.set)
        loop.add_signal_handler(signal.SIGINT, stop.set)

        # Background config polling — pulls fresh light/fan/blower config
        # from active controllers every N minutes so HA stays in sync with
        # SF-App-side changes the user makes without HA interaction.
        poll_task = asyncio.create_task(proxy.config_poll_loop())

        logger.info("Proxy listening on %s:%s", pcfg["listen_host"], pcfg["listen_port"])
        async with server:
            await stop.wait()
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
        logger.info("Shutting down")

    try:
        loop.run_until_complete(run())
    finally:
        mq.loop_stop()
        mq.disconnect()
        loop.close()


if __name__ == "__main__":
    main()

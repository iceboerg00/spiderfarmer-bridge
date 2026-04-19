import logging
import sys

import paho.mqtt.client as mqtt

from proxy.config import load_config
from ha.publisher import DiscoveryPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config("config/config.yaml")
    mqcfg = config["mosquitto"]

    mq = mqtt.Client(client_id="sf-bridge-discovery")
    mq.connect(mqcfg["host"], mqcfg["port"], keepalive=60)

    publisher = DiscoveryPublisher(config, mq)
    publisher.start()

    try:
        mq.loop_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        mq.disconnect()


if __name__ == "__main__":
    main()

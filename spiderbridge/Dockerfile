ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 py3-pip \
    hostapd \
    dnsmasq \
    mosquitto \
    mosquitto-clients \
    iptables \
    iw \
    wireless-tools \
    jq

COPY app/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

COPY app/proxy/ /usr/share/spiderbridge/proxy/
COPY app/ha/ /usr/share/spiderbridge/ha/
COPY app/certs/ /usr/share/spiderbridge/certs/
COPY app/main_proxy.py /usr/share/spiderbridge/main_proxy.py
COPY app/main_discovery.py /usr/share/spiderbridge/main_discovery.py

COPY integration/ /usr/share/spiderbridge-integration/

COPY rootfs /

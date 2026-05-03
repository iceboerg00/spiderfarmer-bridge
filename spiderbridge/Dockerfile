ARG BUILD_FROM

# ── Stage 1: build the GGS Lovelace card ─────────────────────────────────────
# Lit/TypeScript card lives in frontend/. We bundle it during the addon
# build so HA users get a single drop-in install — no separate HACS step
# needed. The built ggs-card.js is copied into the runtime image and the
# 03-install-card cont-init script registers it as a Lovelace resource.
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
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
    jq \
    curl

COPY app/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

COPY app/proxy/ /usr/share/spiderbridge/proxy/
COPY app/ha/ /usr/share/spiderbridge/ha/
COPY app/certs/ /usr/share/spiderbridge/certs/
COPY app/main_proxy.py /usr/share/spiderbridge/main_proxy.py
COPY app/main_discovery.py /usr/share/spiderbridge/main_discovery.py

COPY integration/ /usr/share/spiderbridge-integration/

COPY --from=frontend-build /build/dist/ggs-card.js /usr/share/spiderbridge/www/ggs-card.js

COPY rootfs /

FROM nginx:alpine

RUN apk add --no-cache openssl

# Générer le certificat auto-signé
RUN mkdir -p /etc/nginx/certs && \
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/selfsigned.key \
    -out /etc/nginx/certs/selfsigned.crt \
    -subj "/C=FR/ST=France/L=Paris/O=OrionTrader/CN=oriontrader"

COPY nginx.conf /etc/nginx/nginx.conf

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM caddy:2-alpine
RUN apk add --no-cache openssl \
    && mkdir -p /etc/caddy/tls \
    && openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -keyout /etc/caddy/tls/localhost.key -out /etc/caddy/tls/localhost.crt \
    -days 3650 -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile

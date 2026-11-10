# syntax=docker/dockerfile:1

# --- Сборка ---
FROM node:20-alpine AS build

WORKDIR /app

# Сначала зависимости: этот слой кэшируется и пересобирается только при
# изменении lock-файла, а не при каждой правке исходников.
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# --- Отдача ---
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

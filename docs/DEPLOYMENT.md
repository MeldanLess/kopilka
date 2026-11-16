# Развёртывание «Копилки»

Схема та же, что у `rest-api`: Docker на сервере, compose под systemd,
наружу — nginx с сертификатом. Отличие одно: кроме API там ещё фронтенд,
и его адрес API зашивается в бандл на этапе сборки образа.

## 1. Что должно быть на сервере

- Ubuntu 22.04 или новее;
- Docker Engine с плагином Compose;
- nginx и certbot;
- домен или поддомен, например `tracker.example.com`.

## 2. Код и конфигурация

```bash
sudo mkdir -p /opt/kopilka
sudo chown "$USER" /opt/kopilka
git clone https://github.com/MeldanLess/kopilka.git /opt/kopilka
cd /opt/kopilka

cp deploy/env.production.example env.production
chmod 600 env.production
```

Заполните `env.production`:

| Переменная | Откуда взять |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | адрес, с которого ходит браузер (для same-origin не нужен) |
| `VITE_API_URL` | `https://ваш-домен/api` — адрес зашивается в бандл фронтенда |
| `API_IMAGE`, `FRONTEND_IMAGE` | теги образов, опубликованных рабочим процессом релиза |

> Файл называется `env.production` и лежит **в корне репозитория**: боевой
> compose-файл ищет переменные по пути `./env.production`. Если положить файл
> в `deploy/`, compose не найдёт его и не запустится.

## 3. Образы

Фронтенд собирается на сервере: адрес API зашивается в бандл на этапе сборки
(Vite подставляет `VITE_API_URL` в код один раз, и в рантайме он уже не
меняется).

```bash
docker compose -f docker-compose.prod.yml build \
  --build-arg VITE_API_URL=https://ваш-домен/api
```

Бэкенд — либо тянется из реестра (образы публикует рабочий процесс релиза
при отправке тега), либо собирается на сервере:

```bash
docker compose -f docker-compose.prod.yml build api
```

## 4. База данных

Схемой владеет Alembic, а не `create_all`. Compose-файл накатывает миграции
до старта API, но первую миграцию стоит проверить отдельно:

```bash
docker compose -f docker-compose.prod.yml up -d db
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

## 5. Приложение как сервис systemd

```bash
sudo cp deploy/kopilka.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kopilka
systemctl status kopilka
```

## 6. nginx и сертификат

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/kopilka
sudo ln -s /etc/nginx/sites-available/kopilka /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

В `deploy/nginx.conf` замените `tracker.example.com` на свой домен — и в блоке
с портом 80, и в блоке с HTTPS, и в путях к сертификату.

```bash
sudo certbot --nginx -d tracker.example.com
```

Проверка:

```bash
curl -s https://tracker.example.com/health
curl -s https://tracker.example.com/api/health
```

## 7. Резервные копии

Данные трекера — это финансы пользователя, поэтому копии снимаются каждую
ночь, а каталог с ними закрыт от всех, кроме владельца.

```bash
sudo cp deploy/kopilka-backup.service /etc/systemd/system/
sudo cp deploy/kopilka-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kopilka-backup.timer
systemctl list-timers kopilka-backup.timer
```

Проверить вручную:

```bash
sudo systemctl start kopilka-backup.service
journalctl -u kopilka-backup.service -n 20
sudo ls -l /opt/kopilka/backups
```

Копии лежат на том же сервере, что и база: это страховка от опечатки, а не от
потери сервера. Копия на другом носителе — отдельная задача.

## 8. Выпуск новой версии

```bash
# Локально
docker build -t ghcr.io/meldanless/kopilka-api:$(git describe --tags --always) backend/
docker build -t ghcr.io/meldanless/kopilka-frontend:$(git describe --tags --always) \
  --build-arg VITE_API_URL=https://ваш-домен/api frontend/
docker push ghcr.io/meldanless/kopilka-api:тег
docker push ghcr.io/meldanless/kopilka-frontend:тег

# На сервере
sudo systemctl reload kopilka
```

## Демо-данные: осторожно

`python -m app.seed` создаёт аккаунт `demo@example.com` с паролем
`demo12345` — пароль опубликован в README, поэтому такой аккаунт годится
только для локального показа.

**На публичном сервере его заводить не надо:** аккаунт с известным паролем на
открытом хосте — это приглашение, а не демо. Если демо-данные нужны для
скриншота, наполните базу на своей машине и сделайте скриншот оттуда.

## Почему именно так

- **Docker, а не PaaS.** «Развёрнуто за nginx на VPS с юнитом systemd» —
  фраза, которую можно защитить на собеседовании; «задеплоено на Render» —
  факт без содержания.
- **База не публикуется на хост.** В стеке разработки PostgreSQL доступен на
  `localhost:5432`, и это удобно. В бою такой порт открыт всему интернету.
- **Секреты только из файла.** Пароль базы и ключ подписи JWT не зашиты в
  образ и не лежат в репозитории.
- **Адрес API — аргумент сборки.** Vite подставляет его в бандл один раз;
  переменная окружения контейнера на это не влияет, поэтому «поменять адрес
  в `.env`» не сработает — нужно пересобрать образ.

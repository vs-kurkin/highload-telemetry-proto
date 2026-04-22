# Highload Telemetry Service

Сервис агрегации и мониторинга телеметрии IoT-устройств. Целевая пропускная способность: 1000+ rps.

## 2. Стек

**Backend:**
- Python 3.12, Django 5.x, Django Channels (WebSockets)
- Redis (Buffer, DLQ, Cache)
- PostgreSQL (Primary Storage)
- Eclipse Mosquitto (MQTT Broker)
- Pytest, Ruff, Mypy

**Frontend:**
- React 18, TypeScript, Vite
- Zustand (State Management)
- Chart.js / react-chartjs-2 (Визуализация)
- Vitest, ESLint

**Simulator (Нагрузочное тестирование):**
- Python 3.12, asyncio, paho-mqtt

**Инфраструктура:**
- Docker, Docker Compose
- Nginx (Reverse Proxy & Static File Serving)

## 3. Технические и архитектурные решения, особенности, фичи

- **Асинхронный Ingress Pipeline:** Эффективный прием MQTT сообщений через Mosquitto с последующей неблокирующей обработкой.
- **Многоуровневая буферизация (Redis):** Использование Redis в качестве промежуточного буфера перед PostgreSQL сглаживает пиковые нагрузки записи.
- **Dead Letter Queue (DLQ):** Изоляция сбойных пакетов (после 3 неудачных попыток записи в БД) в Redis для предотвращения Head-of-Line blocking и сохранения отказоустойчивости конвейера.
- **Оптимизированное хранилище (PostgreSQL):** Массовая вставка (`bulk_create`) и порционная очистка старых данных (Chunked Deletes, `LIMIT 10000`).
- **Событийно-ориентированный UI (WebSockets):** Django Channels транслирует данные клиентам с мультиплексированием — отправка только по явному запросу подписки (`subscribe`).
- **Frontend Throttling и Мемоизация:** Использование Zustand для буферизации обновлений состояния и `React.memo` для минимизации лишних рендеров графиков при высокой частоте входящих метрик.
- **Безопасность:**
  - Доступ к API и WebSockets по JWT (`HttpOnly`) и статическим токенам (`401 Unauthorized` при отсутствии).
  - Аутентификация IoT-устройств через MQTT-пароли с изоляцией топиков.
  - Строгая валидация входящих JSON-payload'ов.

## 4. Развертывание

```bash
# Клонирование репозитория
git clone https://github.com/vs-kurkin/highload-telemetry-proto.git
cd highload-telemetry-proto

# Запуск всех сервисов в фоновом режиме (БД, Redis, MQTT, Backend, Frontend, Simulator)
pnpm docker:up
```

Доступные интерфейсы после запуска:
- **Frontend (UI):** [http://localhost:80](http://localhost:80) или порт, указанный в Nginx.
- **Backend API:** [http://localhost:8000/api/](http://localhost:8000/api/)
- **MQTT Broker:** `localhost:1883`

## 5. Конфигурирование

Конфигурация осуществляется преимущественно через переменные окружения (`.env` файлы).

Доступные переменные окружения:

**База данных (PostgreSQL & Backend):**
- `DB_NAME` — имя базы данных (по умолчанию: `telemetry_db`)
- `DB_USER` — пользователь БД (по умолчанию: `telemetry_user`)
- `DB_PASSWORD` — пароль пользователя БД (по умолчанию: `supersecretpassword`)
- `DB_HOST` — хост для подключения (по умолчанию: `db`)
- `DB_PORT` — порт для подключения (по умолчанию: `5432`)

**Кэш и Буфер (Redis):**
- `REDIS_HOST` — хост подключения к Redis (по умолчанию: `redis`)
- `REDIS_PORT` — порт Redis (по умолчанию: `6379`)

**MQTT Брокер (Mosquitto & Consumer):**
- `MQTT_HOST` — хост MQTT брокера (по умолчанию: `mosquitto`)
- `MQTT_PORT` — порт MQTT брокера (по умолчанию: `1883`)
- `MQTT_RATE_LIMIT_SECONDS` — интервал троттлинга (ограничения частоты) для сохранения метрик конкретного робота (в секундах)
- `HOSTNAME` — имя хоста, используется как часть уникального `client_id` для MQTT-консьюмера

**Django Backend / Frontend Nginx:**
- `SECRET_KEY` — секретный ключ Django для криптографических операций (по умолчанию: `unsafe`)
- `REMOTE_HOST_IP` — IP-адрес для настройки `ALLOWED_HOSTS` в Django и proxy_pass в конфигурации Nginx (по умолчанию: `127.0.0.1`)

**Simulator (Генерация нагрузки):**
- `NUM_ROBOTS` — количество эмулируемых IoT-устройств (по умолчанию: `50`)
- `UPDATE_INTERVAL` — интервал отправки метрик в секундах (по умолчанию: `0.1` — 100ms)
- `BATTERY_DRAIN_MIN` — минимальный шаг разряда батареи за тик (по умолчанию: `0.01`)
- `BATTERY_DRAIN_MAX` — максимальный шаг разряда батареи за тик (по умолчанию: `0.05`)
- `CRITICAL_FAILURE_CHANCE` — шанс (вероятность) критической поломки сенсора (по умолчанию: `0.001`)
- `LOAD_TOTAL_MESSAGES` — суммарное количество сообщений для режима стресс-тестирования (по умолчанию: `10000`)
- `LOAD_CONCURRENCY` — количество одновременных подключений в режиме стресс-тестирования (по умолчанию: `100`)

**Mosquitto (Файловая конфигурация):**
Конфигурация MQTT брокера расположена в `mosquitto.conf`. По умолчанию включена аутентификация по паролю (`allow_anonymous false` и указан `password_file`).

## 6. Тестирование

**Требования для локального запуска:** `pnpm`, `python 3.12`, `pip`.

```bash
# Установка всех зависимостей
pnpm setup

# Запуск тестов backend (Pytest, in-memory SQLite, моки Redis)
pnpm test:backend

# Запуск тестов frontend (Vitest)
pnpm test:frontend

# Запуск тестов симулятора
pnpm test:simulator

# Запуск всех тестов в проекте (Coverage)
pnpm test:coverage
```

### Линтинг и типизация (Zero-Any policy)
```bash
# Проверка типов и статический анализ (Mypy, Ruff, TypeScript, ESLint)
pnpm lint
pnpm typecheck

# Автоформатирование кода
pnpm fix
```

## 7. Нагрузочное тестирование

Для проверки целевой пропускной способности (1000+ rps) в директории `simulator` предусмотрен специальный скрипт нагрузочного тестирования. Он эмулирует высокую конкурентность и генерирует заданное количество метрик.

Конфигурация скрипта осуществляется через файл `simulator/.env.loadtest` или переменные окружения:
- `LOAD_TOTAL_MESSAGES` (по умолчанию: 10000)
- `LOAD_CONCURRENCY` (по умолчанию: 100)
- `NUM_VIRTUAL_ROBOTS` (по умолчанию: 50)

**Запуск теста:**

```bash
# Переход в директорию симулятора и активация окружения (при необходимости)
cd simulator

# Запуск скрипта нагрузочного тестирования
python load_tester.py
```

По завершении теста скрипт выведет в консоль подробный отчет с метриками:
- Общее количество отправленных сообщений
- Затраченное время (Total Duration)
- Пропускная способность (Throughput - msg/sec)
- Средняя задержка отправки (Avg Latency - ms)
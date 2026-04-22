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

Пример минимального `.env` файла в корне или в директории `backend/`:
```env
# База данных
POSTGRES_DB=telemetry
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# MQTT Брокер
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
MQTT_USERNAME=admin
MQTT_PASSWORD=adminpass

# Безопасность
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,backend
```

**Mosquitto:**
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
# Highload Telemetry Service

Сервис агрегации и мониторинга телеметрии IoT-устройств. Целевая пропускная способность: 1000+ rps.

## Архитектура

- **Ingress (Mosquitto):** MQTT-брокер, прием подключений от устройств.
- **Buffer (Redis):** Промежуточное хранение сообщений для сглаживания пиковых нагрузок перед записью в БД.
- **DLQ (Redis):** Очередь недоставленных сообщений (`telemetry_buffer_dlq`). Изолирует сбойные пакеты после 3 неудачных попыток записи в БД (защита от Head-of-Line blocking).
- **Storage (PostgreSQL):** Долгосрочное хранилище. Запись выполняется батчами (`bulk_create`). Очистка устаревших данных — порционная (Chunked Deletes, `LIMIT 10000`).
- **WebSockets (Django Channels):** Трансляция данных клиентам. Реализовано мультиплексирование: отправка только по явному запросу подписки от клиента.

## Оптимизации

- **Асинхронность:** Неблокирующий I/O пайплайн от извлечения из Redis до отправки в WebSockets.
- **Time-Series API:** Read-Only REST эндпоинт `/api/telemetry/` для истории метрик (LimitOffsetPagination, фильтрация).
- **Frontend Throttling:** Накопление обновлений в буфере (Zustand) и рендеринг интерфейса с фиксированным интервалом.
- **Frontend Memoization:** Использование `React.memo` и хуков для предотвращения избыточных рендеров при обновлении отдельных устройств.
- **Connection Pooling:** Пул соединений с БД для высококонкурентной среды.

## Безопасность и Авторизация

- Доступ к API и WebSockets по JWT (`HttpOnly`) и статическим токенам (`401 Unauthorized` при отсутствии).
- Аутентификация устройств по MQTT-паролям для разграничения доступа к топикам.
- База данных и кэш изолированы во внутренней Docker-сети.
- Строгая валидация входящих JSON-схем.

## Типизация и Тестирование

- **Типизация:** Frontend — TypeScript (Zero-Any). Backend — Python Type Hints (PEP 484).
- **Тестирование (GWT):** Unit (Pytest, Vitest, мокирование `asyncio` и Redis), Integration (in-memory SQLite), Resilience (проверка перенаправления в DLQ при отказах БД).

## Развертывание

```bash
docker buildx bake
pnpm compose:up
```

---
**Technical Specification Compliance:** 2.0.0 (Highload Telemetry Resilience & API v2)
**Project:** NetAgent / Highload Telemetry

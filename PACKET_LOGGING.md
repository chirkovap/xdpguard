# Логирование пакетов в XDPGuard

## Обзор

XDPGuard теперь поддерживает детальное логирование всех сетевых пакетов, проходящих через систему. Эта функция позволяет в реальном времени отслеживать:

- **Source IP** и **Destination IP** каждого пакета
- **Протокол**: TCP, UDP, ICMP или другие
- **Порты** источника и назначения
- **Размер пакета** в байтах
- **Действие**: PASS (пропущен) или DROP (заблокирован)
- **Временная метка** с точностью до наносекунд

## Архитектура

### Компоненты

1. **eBPF программа** (`bpf/xdp_filter_with_logging.c`)
   - Работает на уровне ядра Linux
   - Перехватывает каждый пакет на уровне сетевого интерфейса
   - Извлекает метаданные пакета
   - Отправляет данные через **perf buffer** в userspace

2. **PacketLogger** (`python/packet_logger.py`)
   - Python класс для управления логами
   - Хранит до 10,000 пакетов в памяти (deque)
   - Поддерживает фильтрацию по протоколу и действию
   - Собирает статистику

3. **Web API** (`web/app.py`)
   - REST API endpoints для доступа к логам
   - `/api/packets` - получение логов
   - `/api/packets/stats` - статистика
   - `/api/packets/clear` - очистка логов

4. **Web Dashboard** (`web/templates/dashboard.html`)
   - Третья вкладка "Логи пакетов"
   - Таблица с детальными данными
   - Фильтры и поиск
   - Автообновление каждые 2 секунды

## Установка и Настройка

### 1. Компиляция eBPF программы

```bash
cd bpf/
make

# Или вручную:
clang -O2 -g -target bpf -c xdp_filter_with_logging.c -o xdp_filter_with_logging.o
```

### 2. Установка Python зависимостей

```bash
pip install -r requirements.txt
```

### 3. Конфигурация

Добавьте в `config.yaml`:

```yaml
logging:
  max_packets: 10000          # Максимальное количество пакетов в памяти
  enable_packet_logging: true # Включить логирование пакетов

xdp:
  object_path: "/usr/lib/xdpguard/xdp_filter_with_logging.o"
```

### 4. Запуск

```bash
# Запустить демон
sudo python3 daemon.py

# Запустить web-интерфейс
python3 -m web.app
```

## Использование

### Web Интерфейс

1. Откройте браузер: `http://localhost:5000`
2. Перейдите на вкладку "Логи пакетов"
3. Используйте фильтры:
   - **По действию**: Все / PASS / DROP
   - **По протоколу**: Все / TCP / UDP / ICMP

### API Endpoints

#### Получить логи пакетов

```bash
# Все пакеты
curl http://localhost:5000/api/packets?limit=50

# Только заблокированные
curl http://localhost:5000/api/packets?action=DROP

# Только TCP
curl http://localhost:5000/api/packets?protocol=TCP

# Комбинация фильтров
curl http://localhost:5000/api/packets?action=DROP&protocol=UDP&limit=100
```

#### Статистика

```bash
curl http://localhost:5000/api/packets/stats
```

Пример ответа:
```json
{
  "total": 5342,
  "by_action": {
    "PASS": 4891,
    "DROP": 451
  },
  "by_protocol": {
    "TCP": 3245,
    "UDP": 1897,
    "ICMP": 200
  },
  "recent_count": {
    "last_minute": 89,
    "last_hour": 5342
  }
}
```

#### Очистить логи

```bash
curl -X POST http://localhost:5000/api/packets/clear
```

## Структура данных пакета

```json
{
  "timestamp": "2026-03-04T11:30:45.123456Z",
  "src_ip": "192.168.1.100",
  "dst_ip": "8.8.8.8",
  "protocol": "TCP",
  "src_port": 45678,
  "dst_port": 443,
  "size": 1420,
  "action": "PASS",
  "reason": null
}
```

## Производительность

### Влияние на производительность

- **Логирование выключено**: ~10-15 млн pps
- **Логирование включено**: ~5-8 млн pps

### Оптимизация

Для высоконагруженных систем:

1. **Выборочное логирование**: логируйте только DROP пакеты
2. **Sampling**: логируйте каждый N-й пакет
3. **Уменьшите max_packets**: храните меньше пакетов в памяти

## Управление логированием

### Включить/Выключить логирование

```bash
# Включить
sudo bpftool map update name logging_config key hex 00 00 00 00 value hex 01

# Выключить
sudo bpftool map update name logging_config key hex 00 00 00 00 value hex 00

# Проверить состояние
sudo bpftool map dump name logging_config
```

## Примеры использования

### 1. Мониторинг DDoS атак

Просмотр всех заблокированных пакетов за последнюю минуту:

```bash
curl http://localhost:5000/api/packets?action=DROP&limit=1000 | jq
```

### 2. Анализ трафика

Посмотреть, какие протоколы используются:

```bash
curl -s http://localhost:5000/api/packets/stats | jq '.by_protocol'
```

### 3. Поиск по IP

В web-интерфейсе используйте Ctrl+F для поиска по конкретному IP.

## Интеграция с SIEM

Логи пакетов можно экспортировать в:

- **Elasticsearch/Kibana** (аналог ELK)
- **Splunk**
- **Graylog**
- **Grafana Loki**

Пример отправки в Elasticsearch:

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])

for packet in xdp_manager.get_packet_logs(limit=1000):
    es.index(index='xdpguard-packets', body=packet)
```

## Трублшутинг

### Логи не появляются

1. Проверьте, что логирование включено:
```bash
sudo bpftool map dump name logging_config
```

2. Проверьте, что XDP программа загружена:
```bash
sudo ip link show ens33
```

3. Проверьте логи daemon:
```bash
sudo journalctl -u xdpguard -f
```

### Низкая производительность

Если логирование замедляет систему:

1. Выключите логирование PASS пакетов
2. Увеличьте размер perf buffer
3. Используйте sampling (1 из N пакетов)

## Будущие улучшения

- [ ] Автоматический экспорт в syslog
- [ ] Поддержка IPv6
- [ ] Детальный анализ TCP флагов
- [ ] GeoIP информация
- [ ] Агрегация потоков (NetFlow/sFlow)
- [ ] Machine Learning для обнаружения аномалий

## Лицензия

GPL v3 - см. LICENSE файл

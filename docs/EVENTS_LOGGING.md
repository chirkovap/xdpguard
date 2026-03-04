# Система логирования событий XDPGuard

## Обзор

XDPGuard теперь включает SIEM-подобную систему логирования событий безопасности с веб-интерфейсом для мониторинга в реальном времени.

## Возможности

### Типы событий

- **BLOCK** - IP адрес заблокирован
- **UNBLOCK** - IP адрес разблокирован
- **LOAD** - XDP программа загружена
- **UNLOAD** - XDP программа выгружена
- **SYSTEM** - Системные события
- **DROP** - Пакеты заблокированы
- **ATTACK** - Обнаружена атака

### Уровни серьезности

- **INFO** - Информационные события
- **WARNING** - Предупреждения
- **CRITICAL** - Критические события

## Использование

### Веб-интерфейс

1. Откройте дашборд: `http://your-server-ip:8080`
2. Перейдите на вкладку **"Логи событий"**
3. Используйте фильтры для поиска нужных событий

#### Функции вкладки логов:

- **Фильтрация по типу**: BLOCK, UNBLOCK, SYSTEM, etc.
- **Фильтрация по уровню**: INFO, WARNING, CRITICAL
- **Автоматическое обновление**: Каждые 3 секунды
- **Цветовое кодирование**: События выделены цветом по уровню серьезности
- **Статистика**: Общее количество, за последний час, критические/предупреждения

### REST API

#### Получить события

```bash
# Все события (по умолчанию 100)
curl http://localhost:8080/api/events

# С лимитом
curl http://localhost:8080/api/events?limit=50

# Фильтр по типу
curl http://localhost:8080/api/events?type=BLOCK

# Фильтр по уровню
curl http://localhost:8080/api/events?severity=CRITICAL

# Комбинированные фильтры
curl http://localhost:8080/api/events?type=BLOCK&severity=WARNING&limit=20
```

#### Статистика событий

```bash
curl http://localhost:8080/api/events/stats
```

Ответ:
```json
{
  "total": 156,
  "by_type": {
    "BLOCK": 45,
    "UNBLOCK": 12,
    "SYSTEM": 99
  },
  "by_severity": {
    "INFO": 120,
    "WARNING": 30,
    "CRITICAL": 6
  },
  "recent_count": {
    "last_hour": 23,
    "last_day": 156
  }
}
```

#### Очистить логи

```bash
curl -X POST http://localhost:8080/api/events/clear
```

## Примеры событий

### Блокировка IP

```json
{
  "timestamp": "2026-03-04T12:15:30.123456",
  "type": "BLOCK",
  "severity": "WARNING",
  "ip": "192.168.1.100",
  "message": "IP адрес 192.168.1.100 заблокирован",
  "details": {
    "method": "manual",
    "interface": "eth0"
  }
}
```

### Загрузка XDP

```json
{
  "timestamp": "2026-03-04T10:00:15.987654",
  "type": "LOAD",
  "severity": "INFO",
  "ip": "N/A",
  "message": "XDP программа успешно загружена на eth0",
  "details": {
    "interface": "eth0",
    "mode": "xdpgeneric"
  }
}
```

### Системная ошибка

```json
{
  "timestamp": "2026-03-04T14:30:45.555555",
  "type": "SYSTEM",
  "severity": "CRITICAL",
  "ip": "N/A",
  "message": "XDP программа не найдена: /usr/lib/xdpguard/xdp_filter.o",
  "details": {
    "path": "/usr/lib/xdpguard/xdp_filter.o"
  }
}
```

## Конфигурация

### Максимальное количество событий

По умолчанию система хранит последние **1000 событий**. Чтобы изменить это значение, отредактируйте `python/xdpmanager.py`:

```python
self.event_logger = EventLogger(max_events=5000)  # увеличить до 5000
```

## Интеграция с SIEM

События также записываются в systemd journal:

```bash
# Просмотр всех событий
sudo journalctl -u xdpguard -f

# Фильтр по BLOCK
sudo journalctl -u xdpguard | grep "\[BLOCK\]"

# Фильтр по CRITICAL
sudo journalctl -u xdpguard -p err

# Экспорт в JSON
sudo journalctl -u xdpguard -o json > xdpguard-events.json
```

### Интеграция с rsyslog

Для пересылки логов в централизованную SIEM-систему:

```bash
# Добавьте в /etc/rsyslog.d/xdpguard.conf
if $programname == 'xdpguard' then @@siem-server:514
```

## Примеры использования

### Мониторинг блокировок в реальном времени

```bash
# Watch for BLOCK events
watch -n 1 'curl -s http://localhost:8080/api/events?type=BLOCK&limit=10 | jq .'
```

### Поиск критических событий

```bash
curl -s http://localhost:8080/api/events?severity=CRITICAL | jq '.events[] | "\(.timestamp) - \(.message)"'
```

### Статистика блокировок

```bash
curl -s http://localhost:8080/api/events/stats | jq '.by_type.BLOCK'
```

## Логи в Python

Для добавления пользовательских событий:

```python
from python.xdpmanager import XDPManager

xdp = XDPManager(config)

# Добавить событие
xdp.event_logger.log_event(
    event_type='ATTACK',
    severity='CRITICAL',
    ip_address='10.0.0.50',
    message='DDoS атака обнаружена',
    details={
        'packets_per_sec': 100000,
        'attack_type': 'SYN Flood'
    }
)

# Получить события
events = xdp.get_events(limit=50, event_type='ATTACK')

# Статистика
stats = xdp.get_event_stats()
print(f"Всего событий: {stats['total']}")
print(f"CRITICAL: {stats['by_severity'].get('CRITICAL', 0)}")
```

## Производительность

- События хранятся в памяти (быстрый доступ)
- Thread-safe реализация с Lock
- Автоматическое удаление старых событий (ограниченный размер deque)
- Нет влияния на производительность XDP

## Troubleshooting

### События не отображаются

```bash
# Проверьте API
curl http://localhost:8080/api/events

# Проверьте логи
sudo journalctl -u xdpguard -n 100

# Перезапустите сервис
sudo systemctl restart xdpguard
```

### Очистка логов при переполнении

События автоматически удаляются после достижения `max_events`. Для ручной очистки:

```bash
curl -X POST http://localhost:8080/api/events/clear
```

## Дополнительные возможности

В будущем планируется:

- [ ] Автоматическое обнаружение DDoS-атак
- [ ] Email/Telegram уведомления
- [ ] Гео-IP информация в событиях
- [ ] Экспорт в Elasticsearch/Splunk
- [ ] Grafana дашборды

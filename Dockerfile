# HHV Parser - Docker образ для Ubuntu 24.04

FROM ubuntu:24.04

# Избегаем интерактивных запросов
ENV DEBIAN_FRONTEND=noninteractive

# Обновляем систему и устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt .
COPY parsers/ ./parsers/
COPY utils/ ./utils/
COPY exceptions.py .
COPY HHV_to_csv.py .
COPY genre.md .

# Создаём виртуальное окружение и устанавливаем зависимости
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем браузеры Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Копируем тестовые данные (опционально)
COPY TEST.txt .
COPY HHV_test2.csv .

# Создаём директорию для результатов
RUN mkdir -p /app/parsed

# Команда по умолчанию
CMD ["python3", "HHV_to_csv.py", "--help"]

# Для запуска парсера:
# docker run --rm -v $(pwd)/output:/app/parsed hhv-parser python3 HHV_to_csv.py --urls TEST.txt --limit 10

 1	# HHV Parser - Docker образ для Ubuntu 24.04
     2	
     3	FROM ubuntu:24.04
     4	
     5	# Избегаем интерактивных запросов
     6	ENV DEBIAN_FRONTEND=noninteractive
     7	
     8	# Обновляем систему и устанавливаем зависимости для Playwright и Python
     9	RUN apt-get update && apt-get install -y \
    10	    python3 \
    11	    python3-venv \
    12	    python3-pip \
    13	    wget \
    14	    ca-certificates \
    15	    fonts-liberation \
    16	    libasound2t64 \
    17	    libatk-bridge2.0-0 \
    18	    libdrm2 \
    19	    libgbm1 \
    20	    libgtk-3-0 \
    21	    libnspr4 \
    22	    libnss3 \
    23	    libxcomposite1 \
    24	    libxdamage1 \
    25	    libxfixes3 \
    26	    libxkbcommon0 \
    27	    libxrandr2 \
    28	    xdg-utils \
    29	    && rm -rf /var/lib/apt/lists/*
    30	
    31	# Устанавливаем рабочую директорию
    32	WORKDIR /app
    33	
    34	# Копируем все файлы проекта
    35	COPY . /app/
    36	
    37	# Создаём виртуальное окружение и устанавливаем зависимости
    38	RUN python3 -m venv /opt/venv
    39	ENV PATH="/opt/venv/bin:$PATH"
    40	
    41	RUN pip install --no-cache-dir --upgrade pip
    42	RUN pip install --no-cache-dir -r requirements.txt
    43	
    44	# Устанавливаем браузеры Playwright
    45	RUN playwright install chromium
    46	RUN playwright install-deps chromium
    47	
    48	# Создаём директорию для результатов
    49	RUN mkdir -p /app/parsed
    50	
    51	# Команда по умолчанию
    52	CMD ["python3", "main.py", "--help"]
    53	
    54	# Для запуска парсера:
    55	# docker run --rm -v $(pwd)/output:/app/parsed hhv-parser python3 HHV_to_csv.py --urls TEST.txt --limit 10
    56	

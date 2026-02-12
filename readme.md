# SkillGraph Backend

Backend API для платформы SkillGraph, разработанный на FastAPI.


## ТРЕБОВАНИЯ


- Python 3.12+
- PostgreSQL
- pip / venv


## УСТАНОВКА ПРОЕКТА


1. Клонировать репозиторий

    git clone <repo_url>

------------------------

2. Создать виртуальное окружение

    python -m venv venv

    Активация:

    Windows:

    venv\Scripts\activate

    Linux / Mac:

    source venv/bin/activate

------------------------

3. Установить зависимости

    pip install -r requirements.txt


## ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (.env)


Создать и заполнить файл .env в корне проекта:

    SERVER_BASE_URL="https://..."

    JWT_SECRET_KEY_env="SECRET_KEY"
    JWT_ACCESS_TOKEN_EXPIRES_env="900"
    JWT_REFRESH_TOKEN_EXPIRES_env="2592000"

    DATABASE_URL="postgresql+asyncpg://user:password@ip:port/database"

    SMTP_HOST=""
    SMTP_PORT=587
    SMTP_USER=""
    SMTP_PASSWORD=""


## ЗАПУСК СЕРВЕРА


    python .main.py



## ДОКУМЕНТАЦИЯ API (необходимо включить в main.py)


    SERVER_URL/docs


## СТРУКТУРА ПРОЕКТА


    core/
    routes/
    schemas/
    static/
    main.py
    models.py


## ФУНКЦИОНАЛЬНОСТЬ


- JWT аутентификация (access + refresh токены)
- Регистрация и вход пользователей
- Подтверждение email
- Система графа навыков
- Тесты и система попыток
- Статистика профиля
- Загрузка аватарок (локальное хранилище)
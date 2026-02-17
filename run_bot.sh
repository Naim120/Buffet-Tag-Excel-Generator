#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "telegram_env" ]; then
    python3 -m venv telegram_env
fi

source telegram_env/bin/activate
pip install -r requirements.txt

python3 telegram_bot/bot.py

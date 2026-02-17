#!/bin/bash
cd "$(dirname "$0")"

if [ -f app.pid ]; then
    PID=$(cat app.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Web App (PID $PID) stopped."
    else
        echo "Web App (PID $PID) was not running."
    fi
    rm app.pid
else
    echo "No app.pid file found."
fi

if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Telegram Bot (PID $PID) stopped."
    else
        echo "Telegram Bot (PID $PID) was not running."
    fi
    rm bot.pid
else
    echo "No bot.pid file found."
fi

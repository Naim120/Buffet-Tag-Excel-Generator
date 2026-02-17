#!/bin/bash
cd "$(dirname "$0")"

# Make sure the base runner scripts are executable
chmod +x run_app.sh
chmod +x run_bot.sh

echo "Starting Web App in background..."
nohup ./run_app.sh > app.log 2>&1 &
echo $! > app.pid
echo "Web App running. PID: $(cat app.pid)"

echo "Starting Telegram Bot in background..."
nohup ./run_bot.sh > bot.log 2>&1 &
echo $! > bot.pid
echo "Telegram Bot running. PID: $(cat bot.pid)"

echo "-----------------------------------"
echo "Processes are running in the background."
echo "You can close this terminal now."
echo "To stop them, run: ./stop_background.sh"

#!/bin/bash
# 1. Encendemos el cerebro en segundo plano (&)
uvicorn main:app --host 0.0.0.0 --port $PORT &

# 2. Esperamos 5 segundos a que el cerebro despierte
sleep 5

# 3. Encendemos el cuerpo
python telegram_bot.py
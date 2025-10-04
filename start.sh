#!/usr/bin/env bash
# Render chạy gunicorn để phục vụ Flask ổn định hơn
gunicorn api.app:app

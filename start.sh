#!/usr/bin/env bash
# Lệnh chạy ứng dụng Flask (api.app là file Flask)
gunicorn api.app:app

#!/usr/bin/env bash
# Tăng thời gian chờ (timeout) lên 300 giây và chỉ định 4 worker ổn định
gunicorn api.app:app -t 300 -w 4

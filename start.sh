#!/usr/bin/env bash
# Tăng thời gian chờ lên 120 giây
gunicorn api.app:app -t 120

#!/bin/bash
# Azure App Service startup: run Gunicorn (set WEBSITES_PORT=8000 in App Service config)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120

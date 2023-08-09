#!/usr/bin/env bash

gunicorn -w 8 --threads 5 app:app

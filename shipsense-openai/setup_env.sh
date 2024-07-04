#!/bin/bash

# Create virtual environment
python3 -m venv shipsense_env

# Activate virtual environment
source shipsense_env/bin/activate

# Install dependencies
pip install Flask SQLAlchemy psycopg2-binary openai sentence-transformers elasticsearch docker

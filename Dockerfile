# Smart LMS ML Pipeline Container
# Includes:
# - ETL
# - Feature Engineering
# - Prediction
#
# Run examples:
# python -m etl.main
# python -m ml.main
# python -m ml.predict_main

# Base image
FROM python:3.11-slim

# Prevent Python output buffering
ENV PYTHONUNBUFFERED=1

# Working directory
WORKDIR /app

# Install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the prediction pipeline needs
COPY etl/ etl/
COPY data/ data/
COPY ml/ ml/

# If you have configuration files
# COPY config/ config/

CMD ["python", "-m", "ml.predict_main"]
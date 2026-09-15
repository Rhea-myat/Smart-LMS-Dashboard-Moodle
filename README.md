# Smart LMS Dashboard — ML and ETL Development

This branch contains the data engineering, machine-learning, and pipeline-automation components developed for the Smart LMS Dashboard project.

> This is a component-development branch. Refer to the repository’s `main` branch for the combined portfolio version containing both the Moodle plugin and the MLOps pipeline.

## Branch Purpose

This branch focuses on:

- Moodle data extraction
- Data cleaning and transformation
- Data-quality validation
- Analytics database integration
- Feature engineering
- Academic and behavioural model experimentation
- Model training and evaluation
- Student-risk prediction
- Prediction and feature storage
- Model monitoring
- Automated pipeline execution

## Automated Pipeline

The pipeline was designed to run as a scheduled background process using Linux cron.

```text
Linux Cron Scheduler
        |
        v
Moodle Data Extraction
        |
        v
Data Transformation and Validation
        |
        v
Analytics Database
        |
        v
Feature Engineering
        |
        v
Model Training and Prediction
        |
        v
Prediction Storage and Monitoring
        |
        v
Moodle Dashboard
```

Pipeline execution logs were generated to help administrators review completed stages and investigate processing failures.

## Repository Structure

```text
.
├── data/                 # Development and generated datasets
├── docs/                 # Setup and deployment documentation
├── etl/                  # Extraction, transformation and loading
├── ml/                   # Feature engineering, models and prediction
├── scripts/              # Supporting automation scripts
├── tests/                # ETL and data-validation tests
├── Dockerfile
├── pipeline_runner.py
├── requirements.txt
└── run_nightly.sh
```

##  Development Environments

### Local Development

- **Python:** 3.12
- **Database:** MySQL
- **Configuration:** Local `.env` file

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local configuration file from the provided template:

```bash
cp .env.example .env
```

Update `.env` using credentials for your own local database:

```dotenv
Database configuration is stored in .env:
DB_HOST=localhost
DB_PORT=8889
DB_NAME=analytics_db
DB_USER=change_me
DB_PASSWORD=change_me
```


### Murdoch VM (Ubuntu Server)

The original pipeline was also developed and tested on a university-managed Ubuntu server.

- **Python:** 3.8.10
- **Database:** MySQL
- **Automation:** Linux cron
- **Configuration:** Server-specific environment variables

Older dependency versions were used where necessary to maintain compatibility with Python 3.8.10.

Access to the original university VM ended when the project was completed.

## Running the Pipeline

After configuring the environment, the pipeline entry point is:

```bash
python pipeline_runner.py
```

The scheduled server workflow used:

```text
run_nightly.sh
```

Execution requirements may vary depending on the Moodle database schema and the selected pipeline configuration.

## Docker
The included Docker configuration provides a consistent and reproducible runtime environment and helps reduce dependency-version differences between development environments.

Build the image:

```bash
docker build -t smart-lms-ml .
```

Runtime database configuration should be supplied through environment variables. Credentials must not be included in the image or committed to Git.

## Testing

The `tests/` directory contains ETL and data-validation checks developed during the project.

The test suite may require a configured local database or suitable synthetic test data.

## Notes

- Local and server environments used different Python and dependency versions.
- The original university VM and Moodle database are no longer accessible.
- A new environment requires its own Moodle database, analytics database, and configuration.




ML & ETL Development (myat-mlops)

This branch contains the machine learning experiments, ETL pipeline, and analytics database integration for the Smart LMS Dashboard project.

Branch Purpose

* ETL pipeline development
* Data cleaning and transformation
* Analytics database integration
* Feature engineering and model experimentation
* Initial predictive analytics implementation

Environment Setup

Local Development

Python version: 3.12

Install dependencies:
pip install -r requirements.txt

Database configuration is stored in .env:
DB_HOST=localhost
DB_PORT=8889
DB_NAME=analytics_db
DB_USER=root
DB_PASSWORD=root

Murdoch VM (Ubuntu Server)
Python version: 3.8.10

Database configuration is stored in .env:
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=analytics_db
DB_USER=<xxxxxxx>
DB_PASSWORD=<xxxxxx>


Notes

* .env files are excluded from Git using .gitignore.
* VM uses older package versions due to Python 3.8 compatibility requirements.

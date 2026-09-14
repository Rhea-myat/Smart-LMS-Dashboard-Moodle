# Smart LMS Dashboard for Moodle

A learning analytics system that combines a Moodle dashboard plugin with a Python ETL and machine learning pipeline.

## Overview

The Smart LMS Dashboard was developed to help educators monitor student engagement, academic performance, course activity, and potential learning risks within Moodle.

The system extracts Moodle data, transforms it into an analytics-ready structure, generates machine learning predictions, and displays the resulting insights through a Moodle dashboard.

This project was originally developed and tested in a university-hosted Moodle environment. Access to the original virtual machine and Moodle database ended when the university project was completed.

## Main Features

- Moodle dashboard integration
- Student engagement and performance analytics
- ETL pipeline for extracting and transforming Moodle data
- Academic and behavioural prediction models
- Model evaluation and monitoring
- Prediction storage for dashboard integration
- Scheduled background processing with Linux cron
- Docker configuration for reproducible deployment

## System Architecture

```text
Moodle Database
      |
      v
Python ETL Pipeline
      |
      v
Analytics Database
      |
      v
Machine Learning Pipeline
      |
      v
Prediction Results
      |
      v
Moodle Dashboard Plugin


## Technologies

- Python
- PHP
- JavaScript
- SQL
- Moodle
- Docker
- Linux
- Cron
- Jupyter Notebook

## Project Status 
The original university VM and Moodle database are no longer accessible, so local execution requires a separate Moodle environment. 


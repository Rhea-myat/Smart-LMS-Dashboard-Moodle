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
```

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

## Dashboard Preview

The following screenshots demonstrate the dashboard using synthetic or sanitized data.

### Dashboard Overview

The unit summary provides an executive overview of student engagement, active and inactive student counts, and the latest scheduled analytics refresh.

![Smart LMS Dashboard overview](docs/images/Picture1.png)


### Predictive Analytics

The predictive analytics view summarizes the current student-risk distribution and compares behavioural and academic risk scores. An adjustable threshold supports the identification of students who may require early intervention.

![Student risk distribution and risk map](docs/images/Picture3.png)

### AI-Assisted Insight Summary

The insight summary translates prediction results into key findings and recommended next steps, helping unit coordinators prioritize student-support actions.

![AI-assisted insight summary](docs/images/Picture6.png)

### Course Configuration

Authorized users can configure email notifications, notification frequency, prediction thresholds, inactivity triggers, and the expected level of LMS participation for each course.

![Course and notification configuration](docs/images/Picture8.png)

### Automated Risk Notification

When configured risk conditions are met, the system sends an automated email notifying the unit coordinator that a new analysis is ready for review.

![Automated Smart LMS risk notification](docs/images/Picture9.png)



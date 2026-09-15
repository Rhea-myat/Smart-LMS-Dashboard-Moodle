# Smart LMS Dashboard — Moodle Plugin

This branch contains the Moodle environment setup and plugin implementation for the Smart LMS Dashboard project.

The plugin presents engagement analytics, academic-performance information, student-risk predictions, and intervention-support features within Moodle.

> This is a component-development branch. Refer to the repository's `main` branch for the combined portfolio version containing both the Moodle plugin and the MLOps pipeline.

## Development and Testing Environment

The plugin was developed and tested using:

- **Moodle:** 4.1
- **PHP:** 7.4
- **Database:** MySQL 8.0
- **Local development environment:** MAMP
- **Local operating system:** macOS
- **University-hosted environment:** Linux

These versions document the environment used during the project. Compatibility with newer Moodle, PHP, or MySQL versions has not been verified.

## Branch Scope

This branch focuses on:

- Moodle development-environment setup
- Smart LMS Dashboard plugin development
- Local plugin installation and testing
- Moodle and analytics database integration
- Dashboard user-interface development
- Role and permission configuration
- Prediction-result integration
- Course-level settings
- Email-notification configuration
- Prediction-feedback and intervention workflows

The Python ETL, machine-learning, monitoring, and pipeline-automation components are maintained separately in the `myat-mlops` development branch.

## Branch Scope

This branch focuses on:

- Moodle development-environment setup
- Smart LMS Dashboard plugin development
- Local plugin installation and testing
- Moodle and analytics database integration
- Dashboard user-interface development
- Role and permission configuration
- Prediction-result integration
- Course-level settings
- Email-notification configuration
- Prediction-feedback and intervention workflows

The Python ETL, machine-learning, monitoring, and pipeline-automation components are maintained separately in the `myat-mlops` development branch.

## Plugin Location

```text
moodle/
└── blocks/
    └── smartlmsdashboard/
        ├── classes/
        │   └── prediction_reader.php
        ├── db/
        │   ├── access.php
        │   ├── install.xml
        │   └── upgrade.php
        ├── js/
        │   └── dashboard.js
        ├── lang/
        │   └── en/
        │       └── block_smartlmsdashboard.php
        ├── block_smartlmsdashboard.php
        ├── index.php
        ├── save_course_config.php
        ├── save_feedback.php
        └── version.php
```

## Main Features

- Unit-level engagement summary
- Active and inactive student counts
- Weekly engagement trends
- Learning-resource usage analysis
- Academic-performance distribution
- Academic and behavioural risk visualization
- Searchable and sortable at-risk student list
- Course-specific risk-threshold configuration
- Email-notification frequency and trigger configuration
- Prediction-feedback recording
- Intervention-status tracking
- Role-based Moodle access
- Display of the latest scheduled analytics results

## Technologies

- Moodle Plugin API
- PHP
- JavaScript
- SQL
- MySQL
- HTML
- CSS
- WampServer
- Linux

## System Integration

```text
MLOps Pipeline
      |
      v
Analytics Database
      |
      v
Prediction Reader
      |
      v
Moodle Dashboard Plugin
      |
      +--------------------+
      |                    |
      v                    v
Dashboard Insights    Email Notifications
                           |
                           v
                 Assigned Unit Coordinators
```


The plugin reads prepared analytics and prediction results from the analytics database. It then presents those results to authorized users within Moodle.

The data extraction, transformation, feature engineering, prediction, and scheduled pipeline processes are handled by the separate MLOps component.

## General Installation Process

A general Moodle plugin installation workflow is:

1. Copy the `smartlmsdashboard` directory into Moodle's `blocks` directory.
2. Sign in to Moodle as an administrator.
3. Open **Site administration > Notifications**.
4. Allow Moodle to detect and install the plugin.
5. Assign the required capabilities to authorized roles.
6. Add the Smart LMS Dashboard block to the appropriate Moodle page.
7. Configure the required course, database, risk, and notification settings.

Example destination:

```text
/path/to/moodle/blocks/smartlmsdashboard
```

## Configuration

The plugin requires access to the appropriate Moodle and analytics database structures.

Configuration may vary according to:

- Moodle version
- PHP version
- MySQL configuration
- Course structure
- User roles and permissions
- Analytics database schema
- Prediction-refresh schedule
- Email configuration

## Related Branches

- `main` - combined and documented portfolio version
- `myat-mlops` - ETL, machine-learning, monitoring, and automation development
- `myat-moodle` - Moodle environment and plugin development

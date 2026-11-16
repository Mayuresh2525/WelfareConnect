
# WelfareConnect – Digital Welfare Guide

A Flask-based web application developed as a **B.Sc. IT Community Engagement Project**. It helps people discover government welfare schemes, understand eligibility and benefits, prepare required documents, and access official application portals.

## Features

- Searches and filters government welfare schemes by keyword and category.
- Helps users find relevant schemes through a profile-based finder.
- Displays scheme summaries, eligibility, benefits, required documents and application steps.
- Provides an interactive document checklist.
- Links users to official government portals for further information and applications.
- Includes a five-question awareness quiz.
- Collects responses through a ten-question awareness survey.
- Displays aggregate survey results and scheme-view statistics on a public dashboard.
- Provides a rule-based Welfare Assistant for scheme-related questions and website guidance.
- Includes an admin dashboard for survey analysis and website activity analytics.
- Tracks activities such as page views, searches, filters and scheme views.

## Technologies Used

- Python
- Flask
- HTML
- CSS
- JavaScript
- SQLite
- JSON

## Project Structure

```text
WelfareConnect/
├── app.py
├── scheme_data.json
├── welfareconnect.db
├── requirements.txt
├── templates/
│   ├── index.html
│   └── admin.html
└── static/
    ├── style.css
    └── script.js
```

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/<your-repository>.git
cd <your-repository>
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## How to Run

Start the Flask application:

```bash
python app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000/
```

The application loads scheme information from `scheme_data.json` and uses SQLite to store survey responses and website activity.

## Database

The SQLite database stores survey responses, scheme views, visitor sessions and activity events. The database tables are initialised by the application.

## Learning Objectives

This project was developed to apply Python and Flask in building a practical web application, work with JSON and SQLite, create interactive frontend features using JavaScript, collect and analyse community survey responses, and understand how technology can improve access to public welfare information.

## Note

WelfareConnect is an independent educational project and is not an official government website. Users should verify scheme details and current requirements through the linked official government portals. Do not publish a database containing real participant information or expose passwords and secret credentials in the public repository.

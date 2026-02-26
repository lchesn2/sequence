# Sequence Game Tracker

A Flask web app for tracking ADP office Sequence game results. Players log in to view the daily play-by-play, while admins can submit new game entries. Stats are aggregated by quarter on the Hall of Fame page.

## Features

- **Role-based access** — Admin and User roles with separate dashboards
- **Game entry submission** — Admins log Sequence, Assist, and Block actions with auto-filled date/time
- **Daily play-by-play** — Searchable, paginated table of today's game activity
- **Hall of Fame** — Quarterly and all-time leaderboards per action type
- **Hall of Shame** — Coming soon
- **Last finisher tracker** — Shows the most recent player to finish an action

## Tech Stack

- Python / Flask
- Flask-Login (authentication)
- Pandas (data processing)
- CSV file storage (`games.csv`)
- Bootstrap 5 + DataTables (frontend)

## Project Structure

```
sequence/
├── mysite/
│   ├── app.py              # Main Flask application
│   ├── templates/
│   │   ├── login.html
│   │   ├── admin.html
│   │   ├── user.html
│   │   ├── halloffame.html
│   │   └── hallofshame.html
│   └── static/             # CSS files
├── games.csv               # Game data storage
├── dailyteams.csv
└── requirements.txt
```

## Setup

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd sequence
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   cd mysite
   python app.py
   ```

   The app will be available at `http://127.0.0.1:5000`.

## Game Data

Game entries are stored in `games.csv` with the following columns:

| Column | Description |
|--------|-------------|
| `date` | Date of the game action |
| `time` | Time of the game action |
| `team` | Team (reserved for future use) |
| `name` | Player name |
| `card` | Card (reserved for future use) |
| `type` | Action type: `Sequence`, `Assist`, or `Block` |

Data is filtered to show entries from **June 25, 2025** onwards. Stats are grouped by calendar quarter (Q1–Q4).

## Deployment

This app is configured for deployment on [PythonAnywhere](https://www.pythonanywhere.com). Point the WSGI configuration to `mysite/app.py`.

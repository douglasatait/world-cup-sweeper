# World Cup Sweepstake Dashboard

This Streamlit app profiles the custom 2026 World Cup sweepstake. It loads the league draw, FIFA rankings, and schedule CSVs in `data/`, highlights fixtures tied to players, and exposes tabs for upcoming matches, the full fixture list, and group standings.

## Prerequisites
- Python 3.10 or newer
- Pip (comes with Python) and optionally `venv`/`virtualenv`

## Setup
```
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
``` 

> **Note:** `requirements.txt` can be generated with `pip freeze > requirements.txt` after installing dependencies such as `streamlit`, `pandas`, `matplotlib`, `plotly`, `altair`, and `openai` if you extend the project.

## Running the app
```
streamlit run sweepstake.py
```

The app expects sterling kick-off times for the 2026 World Cup fixtures (UK timezone). The CSV inputs live in `data/`:
- `sweepstake.csv`: player-team assignments
- `rankings.csv`: FIFA rankings used for weighted summaries
- `world-cup-2026-schedule.csv`: master fixture list referenced by the app

Refresh the CSVs when official data is updated.

## Notes
- The script already localizes kickoff times to UK time and highlights today's matches.
- Keep the data files near the script so the relative paths continue to work.

# 1xBet Crash Predictor

An experimental Python desktop application for recording and statistically analyzing 1xBet Crash round results.

The application provides an Arabic-friendly Tkinter interface, local SQLite logging, CSV export, performance metrics, and charts comparing recorded values with the application's estimates.

> **Important:** This project is an educational/statistical experiment. Crash outcomes are random and cannot be reliably predicted. The estimates and indicators are not guarantees, betting advice, or a way to obtain an advantage over the game.

## Features

- Arabic-friendly desktop interface built with Tkinter.
- Record estimated and actual round multipliers.
- Store session records locally using SQLite.
- Import multiple historical multipliers.
- Export recorded data to CSV.
- View recent error metrics and charts.
- Switch between dark, black, and light themes.
- Use a compact floating recorder window.

## Requirements

- Python 3.10 or newer recommended.
- Tkinter (usually included with standard Python installations; on some Linux distributions it must be installed separately).
- Packages listed in `requirements.txt`.

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/1xbet-crash-predictor.git
cd 1xbet-crash-predictor
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the application:

```bash
python crash_predictor.py
```

On Windows, you can also use:

```bash
py -m pip install -r requirements.txt
py crash_predictor.py
```

## How to use

1. Launch the application.
2. Record the actual multiplier after each round, or import a list of historical results.
3. Review the dashboard metrics and charts.
4. Use the floating recorder for quicker data entry.
5. Export records to CSV if you want to keep a copy.

## Data and privacy

The application creates `crash_data.db` in the same directory as the Python script. **In the current code, this database is automatically deleted when the program exits.** Export your records to CSV before closing the application if you need to retain them.

No game account credentials are required by this application.

## Project structure

```text
1xbet-crash-predictor/
├── crash_predictor.py
├── requirements.txt
└── README.md
```

## Disclaimer

This software is provided for learning, experimentation, and statistical visualization only. It does not connect to 1xBet, access private game data, or guarantee future Crash multipliers. Use it responsibly and do not rely on its estimates for financial decisions.

## License

No license has been added yet. All rights remain with the project owner unless a license is added.

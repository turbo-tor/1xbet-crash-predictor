from pathlib import Path
import zipfile

project = Path("/mnt/data/1xbet-crash-predictor")
readme_path = project / "README.md"

readme = """<div align="center">

# 1xBet Crash Predictor

**An experimental Python desktop application for recording and statistically analyzing Crash round results.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Analytics-150458?logo=pandas&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Charts-11557C)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-informational)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Experimental-orange)

</div>

---

## Overview

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

## Built With

- **Python** — application logic.
- **Tkinter** — desktop graphical interface.
- **Pandas** — data processing and statistical summaries.
- **Matplotlib** — charts and visualization.
- **SQLite** — local result storage.
- **arabic-reshaper** and **python-bidi** — Arabic text rendering support.

## Requirements

- Python 3.10 or newer recommended.
- Tkinter (usually included with standard Python installations; on some Linux distributions it must be installed separately).
- Packages listed in `requirements.txt`.

## Installation

Clone the repository:

```bash
git clone https://github.com/turbo-tor/1xbet-crash-predictor.git
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

## How to Use

1. Launch the application.
2. Record the actual multiplier after each round, or import a list of historical results.
3. Review the dashboard metrics and charts.
4. Use the floating recorder for quicker data entry.
5. Export records to CSV if you want to keep a copy.

## Data and Privacy

The application creates `crash_data.db` in the same directory as the Python script. **In the current code, this database is automatically deleted when the program exits.** Export your records to CSV before closing the application if you need to retain them.

No game account credentials are required by this application.

## Project Structure

```text
1xbet-crash-predictor/
├── crash_predictor.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Disclaimer

This software is provided for learning, experimentation, and statistical visualization only. It does not connect to 1xBet, access private game data, or guarantee future Crash multipliers. Use it responsibly and do not rely on its estimates for financial decisions.

## License

No license has been added yet. All rights remain with the project owner unless a license is added.
"""
readme_path.write_text(readme, encoding="utf-8")

zip_path = Path("/mnt/data/1xbet-crash-predictor-updated.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ["crash_predictor.py", "requirements.txt", "README.md"]:
        p = project / name
        if p.exists():
            z.write(p, arcname=f"1xbet-crash-predictor/{name}")
    # Include .gitignore if it exists in the prepared project folder.
    p = project / ".gitignore"
    if p.exists():
        z.write(p, arcname="1xbet-crash-predictor/.gitignore")

print("تم تحديث README وإعادة تجهيز حزمة المشروع.")
print(f"README: {readme_path}")
print(f"ZIP: {zip_path}")

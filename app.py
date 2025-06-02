from flask import Flask, render_template, request
import requests
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Flask apps

from stations import STATION_MAPPING

app = Flask(__name__)
API_URL = "https://api.ffwc.gov.bd/data_load/seven-days-forecast-waterlevel-24-hours/"

# 1) Build STATION_MAP using the correct key "dangerlevel"
STATION_MAP = {
    station['id']: {
        "name": station['name'],
        "danger_level": float(station.get('dangerlevel')) if station.get('dangerlevel') is not None else None
    }
    for station in STATION_MAPPING if 'id' in station and 'name' in station
}

ALLOWED_STATIONS = [
    "Jamalpur", "Durgapur", "Mymensingh", "B. Baria", "Habiganj", "Bhairabbazar",
    "Derai", "Khaliajuri", "Manu-RB", "Moulvibazar", "Narsingdi", "Sheola",
    "Sherpur-Sylhet", "Sunamganj", "Sylhet"
]

def fetch_data():
    resp = requests.get(API_URL)
    resp.raise_for_status()
    json_body = resp.json()

    all_data = {}
    for id_str, date_dict in json_body.items():
        try:
            station_id = int(id_str)
        except ValueError:
            continue

        station_info = STATION_MAP.get(station_id)
        if not station_info:
            continue

        station_name = station_info["name"]
        danger_level = station_info.get("danger_level")

        if station_name not in ALLOWED_STATIONS:
            continue

        station_data = []
        for date_str, wl_value in date_dict.items():
            try:
                mm, dd, yyyy = map(int, date_str.split("-"))
                iso_date = datetime(yyyy, mm, dd).date().isoformat()
                if isinstance(wl_value, (int, float)):
                    station_data.append({
                        "date": iso_date,
                        "water_level": wl_value
                    })
            except:
                continue

        station_data.sort(key=lambda x: x["date"])
        all_data[station_name] = {
            "data": station_data,
            "danger_level": danger_level
        }

    return all_data

@app.route("/", methods=["GET"])
def index():
    all_data = fetch_data()

    station_plots = []
    for station_name, station_info in all_data.items():
        data = station_info["data"]
        danger_level = station_info["danger_level"]
        plot_url = None

        if data:
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])

            plt.figure(figsize=(10, 5))
            plt.plot(df["date"], df["water_level"], marker="o", label="Water Level")

            if danger_level is not None:
                plt.axhline(y=danger_level, color='orange', linestyle='--', label='Danger Level')
                ymin, ymax = plt.ylim()
                plt.axhspan(danger_level, ymax, color='red', alpha=0.1)

            plt.title(f"Water Level Over Time - {station_name}")
            plt.xlabel("Date")
            plt.ylabel("Water Level (m)")
            plt.legend()
            plt.grid(True)

            img = io.BytesIO()
            plt.savefig(img, format="png")
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode()
            plt.close()

        station_plots.append({
            "station": station_name,
            "danger_level": danger_level,
            "plot_url": plot_url
        })

    return render_template(
        "index.html",
        station_plots=station_plots
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
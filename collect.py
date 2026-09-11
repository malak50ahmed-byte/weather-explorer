from pathlib import Path
from datetime import datetime

import requests

import pandas as pd


def fetch_json(url):
    url_response = requests.get(url)
    url_response.raise_for_status()
    return url_response.json()


today = datetime.now()  # noqa: DTZ005

today_date = today.strftime("%Y-%m-%d")

url = f"https://api.open-meteo.com/v1/forecast?latitude={30.04}&longitude={31.23}&start_date={today_date}&end_date={today_date}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"

try:
    weather_data = fetch_json(url)
except requests.exceptions.RequestException as e:
    print(f"Could not fetch weather data: {e}")
    exit()

# --- Build the DataFrame ---
daily_data = weather_data["daily"]
df = pd.DataFrame(
    {
        "Date": daily_data["time"],
        "Max Temp": daily_data["temperature_2m_max"],
        "Min Temp": daily_data["temperature_2m_min"],
    }
)

path = Path("data.csv")

df.to_csv("data.csv", mode="a", index=False, header=not path.exists())

print(f"Saved {len(df)} rows to data.csv")

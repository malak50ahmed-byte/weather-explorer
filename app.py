from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import requests
import streamlit as st

import pandas as pd

# --- User input ---
# Validate before hitting the APIs so failures are clear, not cryptic
st.title("Weather Explorer")
latitude = st.number_input("Enter the latitude: ", value=30.04)
longitude = st.number_input("Enter the longitude: ", value=31.24)

if st.button("Get Weather"):
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        st.error(
            "Coordinates out of range. Latitude (-90 to 90), Longitude (-180 to 180)"
        )
        st.stop()

    # --- Resolve coordinates to a place name ---
    geo_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={latitude}&longitude={longitude}&localityLanguage=en"

    try:
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

    except requests.exceptions.RequestException as e:
        st.error(f"Could not fetch Geo data: {e}")
        st.stop()

    # Not every coordinate resolves to a city — fall back through broader regions
    city_name = (
        geo_data.get("city")
        or geo_data.get("locality")
        or geo_data.get("principalSubdivision")
        or "Unknown Place"
    )
    country_name = geo_data.get("countryName", "")

    place_name = f"{city_name}, {country_name}" if country_name else city_name
    safe_name = place_name.replace(", ", "_").replace(" ", "_").replace("/", "-")

    st.write(place_name)

    # --- Fetch the past week's temperatures ---
    today = datetime.now()  # noqa: DTZ005
    week_ago = today - timedelta(7)

    start = week_ago.strftime("%Y-%m-%d")  # API expects YYYY-MM-DD
    end = today.strftime("%Y-%m-%d")

    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&start_date={start}&end_date={end}&daily=temperature_2m_max,temperature_2m_min"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as e:
        st.error(f"Could not fetch weather data: {e}")
        st.stop()

    # --- Build the DataFrame ---
    daily_data = data["daily"]
    df = pd.DataFrame(
        {
            "Date": daily_data["time"],
            "Max Temp": daily_data["temperature_2m_max"],
            "Min Temp": daily_data["temperature_2m_min"],
        }
    )

    df["Date"] = pd.to_datetime(df["Date"])
    st.dataframe(df)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(df["Date"], df["Max Temp"], marker="o", label="Max Temp")
    ax.plot(df["Date"], df["Min Temp"], marker="o", label="Min Temp")

    ax.set_title(f"{place_name} Weather", pad=20)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    st.pyplot(fig)
    st.download_button(
        "Download CSV", df.to_csv(index=False), f"{safe_name}_weather.csv"
    )

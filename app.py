from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import requests
import streamlit as st

import pandas as pd


# --- Helpers ---

def shift_year(d, year):
    # Feb 29 doesn't exist in non-leap years — fall back to the 28th
    try:
        return d.replace(year=year)
    except ValueError:
        return d.replace(year=year, day=28)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_json(url):
    # Cached so repeat searches don't re-hit the APIs
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


# --- Interface ---
st.title("Weather Explorer")
latitude = st.number_input("Enter the latitude: ", value=30.04)
longitude = st.number_input("Enter the longitude: ", value=31.24)

if st.button("Get Weather"):
    with st.spinner("Fetching Weather Data ......"):
        # Validate before hitting the APIs so failures are clear, not cryptic
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            st.error(
                "Coordinates out of range. Latitude (-90 to 90), Longitude (-180 to 180)"
            )
            st.stop()

        # --- Resolve coordinates to a place name ---
        geo_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={latitude}&longitude={longitude}&localityLanguage=en"

        try:
            geo_data = fetch_json(geo_url)

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

        # --- Historical baseline: same week, each of the past 10 years ---
        today = datetime.now()  # noqa: DTZ005
        week_ago = today - timedelta(7)
        years_ago = []
        try:
            for year in range(today.year - 10, today.year):
                old_start = shift_year(week_ago, year).strftime("%Y-%m-%d")
                old_end = shift_year(today, year).strftime("%Y-%m-%d")

                archive_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={old_start}&end_date={old_end}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"

                archive_data = fetch_json(archive_url)

                temps = archive_data["daily"]["temperature_2m_max"]
                c = sum(temps) / len(temps)
                years_ago.append(c)

        # The baseline is a bonus — warn, but let the rest of the app run
        except (requests.exceptions.RequestException, KeyError, ZeroDivisionError) as e:
            st.warning(f"Historical data unavailable: {e}")

        # --- This week's temperatures ---
        start = week_ago.strftime("%Y-%m-%d")  # API expects YYYY-MM-DD
        end = today.strftime("%Y-%m-%d")

        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&start_date={start}&end_date={end}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"

        try:
            weather_data = fetch_json(url)
        except requests.exceptions.RequestException as e:
            st.error(f"Could not fetch weather data: {e}")
            st.stop()

    # --- Build the DataFrame ---
    daily_data = weather_data["daily"]
    df = pd.DataFrame(
        {
            "Date": daily_data["time"],
            "Max Temp": daily_data["temperature_2m_max"],
            "Min Temp": daily_data["temperature_2m_min"],
        }
    )

    df["Date"] = pd.to_datetime(df["Date"])  # so matplotlib reads them as dates, not text
    df["Range"] = df["Max Temp"] - df["Min Temp"]  # daily swing — wider in dry climates

    # --- Summary statistics ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Average Max", value=f"{df['Max Temp'].mean():.1f}°C")
    c2.metric(label="Highest", value=f"{df['Max Temp'].max():.1f}°C")
    c3.metric(label="Lowest", value=f"{df['Min Temp'].min():.1f}°C")
    c4.metric(label="Avg Daily Range", value=f"{df['Range'].mean():.1f}°C")

    st.dataframe(df)

    # --- How this week compares to the 10-year average ---
    current_average = df["Max Temp"].mean()
    if years_ago:
        historical_average = sum(years_ago) / len(years_ago)
        difference = current_average - historical_average

        st.metric(
            label="vs. 10-year average",
            value=f"{current_average:.1f}°C",
            delta=f"{difference:.1f}°C",
        )
    else:
        st.info("10-year comparison not available.")

    # --- Plot ---
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.plot(df["Date"], df["Max Temp"], marker="o", label="Max Temp")
    ax.plot(df["Date"], df["Min Temp"], marker="o", label="Min Temp")

    ax.set_title(f"{place_name} Weather", pad=20)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()  # keeps the angled date labels from being cut off

    st.pyplot(fig)
    st.download_button(
        "Download CSV", df.to_csv(index=False), f"{safe_name}_weather.csv"
    )

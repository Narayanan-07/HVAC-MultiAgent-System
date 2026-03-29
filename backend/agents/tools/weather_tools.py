import time
import json
import httpx
from crewai.tools import tool

@tool("Weather API Fetcher")
def fetch_weather_forecast(lat: float, lon: float, days: int) -> str:
    """
    Call Open-Meteo API to fetch weather forecast.
    Parameters: latitude, longitude, and forecast_days=days.
    Returns: JSON string with hourly timestamp, temperature_2m, relativehumidity_2m, dewpoint_2m.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relativehumidity_2m,dewpoint_2m",
        "forecast_days": days
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                hourly = []
                if "hourly" in data:
                    times = data["hourly"].get("time", [])
                    temps = data["hourly"].get("temperature_2m", [])
                    hums = data["hourly"].get("relativehumidity_2m", [])
                    dews = data["hourly"].get("dewpoint_2m", [])
                    
                    for i in range(len(times)):
                        hourly.append({
                            "timestamp": times[i],
                            "temperature_2m": temps[i] if i < len(temps) else None,
                            "relativehumidity_2m": hums[i] if i < len(hums) else None,
                            "dewpoint_2m": dews[i] if i < len(dews) else None
                        })
                
                return json.dumps({"hourly": hourly})
                
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                # Graceful degradation on failure: instruct to use last known weather
                return json.dumps({
                    "error": str(e),
                    "hourly": [],
                    "message": "API timeout or failure. Fallback to last known weather from data."
                })

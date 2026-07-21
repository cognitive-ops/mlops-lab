"""
Weather Agent – real-time weather data retrieval.
"""

import os
from datetime import datetime

import requests
from google.genai import types

from .base_agent import BaseAgent


def get_weather(city: str):
    """Get current weather for a city using real weather APIs."""
    openweather_key = os.getenv("OPENWEATHER_API_KEY")

    if openweather_key:
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": openweather_key, "units": "metric"}
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "city": city,
                "temperature": round(data["main"]["temp"], 1),
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": round(data["wind"]["speed"] * 3.6, 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "pressure": data["main"]["pressure"],
                "timestamp": datetime.now().isoformat(),
                "source": "OpenWeatherMap",
            }
        except Exception:
            pass  # fall through to wttr.in

    try:
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data["current_condition"][0]
        return {
            "city": city,
            "temperature": int(current["temp_C"]),
            "condition": current["weatherDesc"][0]["value"],
            "humidity": int(current["humidity"]),
            "wind_speed": int(current["windspeedKmph"]),
            "feels_like": int(current["FeelsLikeC"]),
            "pressure": int(current["pressure"]),
            "visibility": int(current["visibility"]),
            "uv_index": int(current["uvIndex"]),
            "timestamp": datetime.now().isoformat(),
            "source": "wttr.in",
        }
    except Exception as exc:
        return {
            "city": city,
            "error": f"Failed to fetch weather data: {exc}",
            "success": False,
            "timestamp": datetime.now().isoformat(),
        }


def get_forecast(city: str, days: int = 3):
    """Get weather forecast for the next N days (simulated)."""
    return {
        "city": city,
        "days": days,
        "forecast": [
            {"day": i + 1, "high": 25 + i, "low": 15 +
                i, "condition": "Partly Cloudy"}
            for i in range(days)
        ],
        "note": "Simulated forecast – replace with a real API in production.",
    }


_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_weather",
        description="Get current weather information for a specified city.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING",
                    "description": "Name of the city to get weather for",
                }
            },
            "required": ["city"],
        },
    ),
    types.FunctionDeclaration(
        name="get_forecast",
        description="Get weather forecast for the next N days in a specified city.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING",
                    "description": "Name of the city",
                },
                "days": {
                    "type": "INTEGER",
                    "description": "Number of forecast days (1-7, default 3)",
                },
            },
            "required": ["city"],
        },
    ),
]

_FUNCTIONS = {"get_weather": get_weather, "get_forecast": get_forecast}


class WeatherAgent(BaseAgent):
    name = "weather_agent"
    description = (
        "Specialises in weather – fetches current conditions and forecasts "
        "for any city, and provides weather-related advice."
    )

    def _build_tools(self):
        return _DECLARATIONS, _FUNCTIONS

    def _system_instruction(self) -> str:
        return (
            "You are a **Weather Agent**. Your job is to retrieve and interpret "
            "weather data. Provide clear summaries that include temperature, "
            "conditions, humidity and any notable alerts. Be helpful with travel "
            "or activity recommendations based on weather."
        )

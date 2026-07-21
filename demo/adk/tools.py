"""
Tool definitions and implementations for the Agentic AI.
"""

from google.genai import types
import requests
from datetime import datetime
import math
import os
from typing import Dict, Any


# Tool function implementations
def calculate(expression: str) -> Dict[str, Any]:
    """
    Calculate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        Result of the calculation
    """
    try:
        # Safe evaluation of mathematical expressions
        allowed_names = {
            'sqrt': math.sqrt,
            'pow': math.pow,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'pi': math.pi,
            'e': math.e,
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {
            "success": True,
            "result": result,
            "expression": expression
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "expression": expression
        }


def get_weather(city: str) -> Dict[str, Any]:
    """
    Get current weather for a city using real weather APIs.

    Uses wttr.in API (no key required) as primary source.
    Falls back to OpenWeatherMap if OPENWEATHER_API_KEY is set.

    Args:
        city: Name of the city

    Returns:
        Weather information with temperature, condition, humidity, etc.
    """
    # Try OpenWeatherMap first if API key is available
    openweather_key = os.getenv("OPENWEATHER_API_KEY")

    if openweather_key:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": city,
                "appid": openweather_key,
                "units": "metric"  # Celsius
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "city": city,
                "temperature": round(data["main"]["temp"], 1),
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                # m/s to km/h
                "wind_speed": round(data["wind"]["speed"] * 3.6, 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "pressure": data["main"]["pressure"],
                "timestamp": datetime.now().isoformat(),
                "source": "OpenWeatherMap"
            }
        except Exception as e:
            # Fall through to wttr.in if OpenWeatherMap fails
            pass

    # Use wttr.in as fallback (no API key needed)
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

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
            "source": "wttr.in"
        }
    except Exception as e:
        return {
            "city": city,
            "error": f"Failed to fetch weather data: {str(e)}",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }


def search_web(query: str) -> Dict[str, Any]:
    """
    Search the web for information (simulated).

    Args:
        query: Search query

    Returns:
        Search results
    """
    # This is a simulated response for demo purposes
    # In production, you'd call a real search API (Google Custom Search, Bing, etc.)

    return {
        "query": query,
        "results": [
            {
                "title": f"Result 1 for '{query}'",
                "snippet": "This is a simulated search result. In production, use a real search API.",
                "url": "https://example.com/result1"
            },
            {
                "title": f"Result 2 for '{query}'",
                "snippet": "Another simulated result demonstrating the search functionality.",
                "url": "https://example.com/result2"
            }
        ],
        "total_results": 2
    }


def save_note(title: str, content: str) -> Dict[str, Any]:
    """
    Save a note to a file.

    Args:
        title: Title of the note
        content: Content of the note

    Returns:
        Status of the save operation
    """
    try:
        filename = f"notes_{title.replace(' ', '_')}.txt"
        with open(filename, 'w') as f:
            f.write(f"Title: {title}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"\n{content}\n")

        return {
            "success": True,
            "filename": filename,
            "title": title
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
    """
    Get current time in a specific timezone.

    Args:
        timezone: Timezone name (default: UTC)

    Returns:
        Current time information
    """
    now = datetime.now()
    return {
        "timezone": timezone,
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A")
    }


# Tool declarations for Google Gemini (new google.genai SDK format)
# These define the interface that the AI model sees

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="calculate",
        description="Calculate a mathematical expression. Supports basic operations (+, -, *, /), functions like sqrt, sin, cos, and constants like pi and e.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "expression": {
                    "type": "STRING",
                    "description": "Mathematical expression to evaluate, e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)'"
                }
            },
            "required": ["expression"]
        }
    ),
    types.FunctionDeclaration(
        name="get_weather",
        description="Get current weather information for a specified city.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "city": {
                    "type": "STRING",
                    "description": "Name of the city to get weather for"
                }
            },
            "required": ["city"]
        }
    ),
    types.FunctionDeclaration(
        name="search_web",
        description="Search the web for information on a given topic.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search query or topic to look up"
                }
            },
            "required": ["query"]
        }
    ),
    types.FunctionDeclaration(
        name="save_note",
        description="Save a note with a title and content to a file.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Title of the note"
                },
                "content": {
                    "type": "STRING",
                    "description": "Content/body of the note"
                }
            },
            "required": ["title", "content"]
        }
    ),
    types.FunctionDeclaration(
        name="get_current_time",
        description="Get the current date and time in a specified timezone.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "timezone": {
                    "type": "STRING",
                    "description": "Timezone name (e.g., 'UTC', 'EST', 'PST')"
                }
            }
        }
    )
]


# Map function names to their implementations
TOOL_FUNCTIONS = {
    "calculate": calculate,
    "get_weather": get_weather,
    "search_web": search_web,
    "save_note": save_note,
    "get_current_time": get_current_time
}

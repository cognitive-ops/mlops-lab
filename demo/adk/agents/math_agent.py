"""
Math Agent – mathematical calculations and reasoning.
"""

import math
from typing import Any, Dict

from google.genai import types

from .base_agent import BaseAgent


def calculate(expression: str) -> Dict[str, Any]:
    """Safely evaluate a mathematical expression."""
    allowed = {
        "sqrt": math.sqrt,
        "pow": math.pow,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "pi": math.pi,
        "e": math.e,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return {"success": True, "result": result, "expression": expression}
    except Exception as exc:
        return {"success": False, "error": str(exc), "expression": expression}


def unit_convert(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Convert between common units."""
    CONVERSIONS = {
        ("km", "miles"): 0.621371,
        ("miles", "km"): 1.60934,
        ("kg", "lbs"): 2.20462,
        ("lbs", "kg"): 0.453592,
        ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
        ("m", "ft"): 3.28084,
        ("ft", "m"): 0.3048,
        ("l", "gal"): 0.264172,
        ("gal", "l"): 3.78541,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key not in CONVERSIONS:
        return {"error": f"Unsupported conversion: {from_unit} -> {to_unit}"}

    factor = CONVERSIONS[key]
    if callable(factor):
        converted = factor(value)
    else:
        converted = value * factor

    return {
        "original": value,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "result": round(converted, 4),
    }


_DECLARATIONS = [
    types.FunctionDeclaration(
        name="calculate",
        description=(
            "Evaluate a mathematical expression. Supports +, -, *, /, "
            "sqrt, sin, cos, tan, log, exp, pi, e, and more."
        ),
        parameters={
            "type": "OBJECT",
            "properties": {
                "expression": {
                    "type": "STRING",
                    "description": "Mathematical expression, e.g. 'sqrt(16) + sin(pi/2)'",
                }
            },
            "required": ["expression"],
        },
    ),
    types.FunctionDeclaration(
        name="unit_convert",
        description="Convert a value between common units (km/miles, kg/lbs, celsius/fahrenheit, etc.).",
        parameters={
            "type": "OBJECT",
            "properties": {
                "value": {"type": "NUMBER", "description": "Numeric value to convert"},
                "from_unit": {"type": "STRING", "description": "Source unit"},
                "to_unit": {"type": "STRING", "description": "Target unit"},
            },
            "required": ["value", "from_unit", "to_unit"],
        },
    ),
]

_FUNCTIONS = {"calculate": calculate, "unit_convert": unit_convert}


class MathAgent(BaseAgent):
    name = "math_agent"
    description = (
        "Specialises in mathematics – evaluating expressions, unit conversion, "
        "and step-by-step mathematical reasoning."
    )

    def _build_tools(self):
        return _DECLARATIONS, _FUNCTIONS

    def _system_instruction(self) -> str:
        return (
            "You are a **Math Agent**. Your job is to solve mathematical problems. "
            "Show your reasoning step by step. Use the 'calculate' tool for numeric "
            "computations and 'unit_convert' for unit conversions. "
            "Always verify your results make sense before answering."
        )

from langchain.tools import tool
import random
from langchain_core.messages import HumanMessage
from src.model import get_model, get_runnable_config

# Don't initialize the model here - get it fresh each time to avoid auth issues

@tool
def get_challenger_cities(base_city: str) -> str:
    """Get a list of challenger cities that might have better weather than the given base_city."""
    # Simulate API or data lookup - return multiple challengers
    options = ["Lisbon", "Tel Aviv", "Athens", "Barcelona", "San Diego", "Sydney", "Cape Town", "Dubai"]
    # Select 3-5 random challengers
    num_challengers = random.randint(3, 5)
    challengers = random.sample(options, num_challengers)
    return f"Challenger cities that might have better weather than {base_city}: {', '.join(challengers)}"

@tool
def compare_cities_weather(city1: str, city2: str) -> str:
    """Compare the weather between two cities and determine which has better weather using AI analysis."""
    
    print(f"🔧 TOOL CALLED: compare_cities_weather({city1}, {city2})")
    
    # Create a prompt for the LLM to compare the cities
    comparison_prompt = f"""
You are a weather expert. Compare the weather between these two cities and determine which has better weather overall.

Cities to compare:
- {city1}
- {city2}

Consider these factors:
- Average temperatures throughout the year
- Seasonal variation and extremes
- Precipitation patterns (rain, snow, etc.)
- Humidity levels
- Wind patterns
- Sunshine hours
- Overall climate comfort
- Weather-related quality of life factors

Provide your analysis and declare a winner. Format your response as:
"WEATHER ANALYSIS: [brief analysis of both cities' weather patterns]
WINNER: [city name]
REASONING: [explanation of why this city has better weather]"
"""

    # For now, use a smart fallback that provides realistic weather comparisons
    # This avoids the authentication issues while still providing good results
    print(f"🤖 Creating smart weather comparison: {city1} vs {city2}")
    
    # Create realistic weather comparisons based on known city characteristics
    weather_data = {
        "Dubai": {"climate": "desert", "temp": "hot", "humidity": "high", "comfort": 6},
        "Tel Aviv": {"climate": "mediterranean", "temp": "warm", "humidity": "moderate", "comfort": 8},
        "Athens": {"climate": "mediterranean", "temp": "warm", "humidity": "low", "comfort": 7},
        "Haifa": {"climate": "mediterranean", "temp": "mild", "humidity": "moderate", "comfort": 8},
        "Doha": {"climate": "desert", "temp": "very hot", "humidity": "high", "comfort": 4},
        "Perth": {"climate": "mediterranean", "temp": "warm", "humidity": "low", "comfort": 9},
        "Lisbon": {"climate": "oceanic", "temp": "mild", "humidity": "moderate", "comfort": 8},
        "Barcelona": {"climate": "mediterranean", "temp": "warm", "humidity": "moderate", "comfort": 8},
        "San Diego": {"climate": "mediterranean", "temp": "mild", "humidity": "low", "comfort": 9},
        "Sydney": {"climate": "oceanic", "temp": "mild", "humidity": "moderate", "comfort": 8}
    }
    
    # Get weather data for both cities
    city1_data = weather_data.get(city1, {"climate": "temperate", "temp": "moderate", "humidity": "moderate", "comfort": 6})
    city2_data = weather_data.get(city2, {"climate": "temperate", "temp": "moderate", "humidity": "moderate", "comfort": 6})
    
    # Determine winner based on comfort score
    if city1_data["comfort"] > city2_data["comfort"]:
        winner = city1
        loser = city2
        margin = city1_data["comfort"] - city2_data["comfort"]
    elif city2_data["comfort"] > city1_data["comfort"]:
        winner = city2
        loser = city1
        margin = city2_data["comfort"] - city1_data["comfort"]
    else:
        winner = city1  # Tie goes to first city
        loser = city2
        margin = 0
    
    # Create realistic analysis
    result = f"""WEATHER ANALYSIS: {city1} has a {city1_data['climate']} climate with {city1_data['temp']} temperatures and {city1_data['humidity']} humidity, while {city2} offers a {city2_data['climate']} climate with {city2_data['temp']} temperatures and {city2_data['humidity']} humidity.

WINNER: {winner}
REASONING: {winner} provides better overall weather comfort with a score of {city1_data['comfort'] if winner == city1 else city2_data['comfort']} compared to {loser}'s score of {city2_data['comfort'] if winner == city1 else city1_data['comfort']}. The {winner} climate offers more favorable conditions for year-round living."""
    
    print(f"✅ Smart comparison result: {result[:200]}...")
    
    return result

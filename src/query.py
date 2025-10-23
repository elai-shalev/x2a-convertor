import structlog


from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from langgraph.prebuilt import create_react_agent
from tools.weather_tools import get_challenger_cities, compare_cities_weather


from typing import TypedDict
from src.model import get_model, get_runnable_config


logger = structlog.get_logger(__name__)

class QueryResponse(BaseModel):
    """Structured output for query response"""

    response: str


class VictorCityResponse(BaseModel):
    """Structured output for victor city extraction"""
    
    victor_city: str
    reasoning: str


class QueryState(TypedDict):
    city_1: str
    city_2: str
    city_1_weather: str
    city_2_weather: str
    better_city: str
    weather_comparison: str
    challenger_cities: list[str]
    tournament_results: list[dict[str, str]]
    final_victor: str
    messages: list[dict[str, str]]
    remaining_steps: int


class QueryWorkflow:
    def __init__(self, model=None) -> None:
        self.model = model or get_model()
        self.graph = self._build_graph()
        self.agent_find_better_city = self._build_agent_find_better_city()
        print(self.graph.get_graph().draw_mermaid())

    def _build_agent_find_better_city(self):
        """Create a LangGraph agent that can run the entire tournament"""
        logger.info("Creating tournament agent")

        tools = [
            get_challenger_cities,
            compare_cities_weather,
        ]

        # pyrefly: ignore
        agent = create_react_agent(
            model=self.model,
            tools=tools,
            state_schema=AgentStatePydantic,
        )
        return agent

    def _build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(dict)

        workflow.add_node("query_city_1_weather", lambda state: self.weather_query(state, 1))
        workflow.add_node("query_city_2_weather", lambda state: self.weather_query(state, 2))
        workflow.add_node("compare_weather", lambda state: self.compare_weather(state))
        workflow.add_node("agent_run_tournament", lambda state: self.agent_run_tournament(state))

        workflow.set_entry_point("query_city_1_weather")
        workflow.add_edge("query_city_1_weather", "query_city_2_weather")
        workflow.add_edge("query_city_2_weather", "compare_weather")
        workflow.add_edge("compare_weather", "agent_run_tournament")
        workflow.add_edge("agent_run_tournament", END)

        return workflow.compile()

    def weather_query(self, state: QueryState, city_number: int) -> QueryState:
        """Query the llm for weather information for a given city"""
        if city_number == 1:
            city = state["city_1"]
        else:
            city = state["city_2"]
        
        print(f"\n🌤️  Getting weather for {city}...")
        
        weather_prompt = (
            f"What is the current weather in {city}? Please provide a "
            "detailed weather report including temperature, conditions, "
            "humidity, and any other relevant weather information."
        )

        messages = [
            {"role": "user", "content": weather_prompt},
        ]
        structured_llm = self.model.with_structured_output(QueryResponse)
        response = structured_llm.invoke(
            messages, config=get_runnable_config()
        )
        state[f"city_{city_number}_weather"] = response.response
        
        print(f"✅ Weather for {city}: {response.response[:100]}...")
        return state
    
    def compare_weather(self, state: QueryState) -> QueryState:
        """Compare the weather of the two cities"""
        city_1_weather = state["city_1_weather"]
        city_2_weather = state["city_2_weather"]

        print(f"\n⚖️  Comparing weather: {state['city_1']} vs {state['city_2']}...")

        compare_weather_prompt = (
            f"Compare the weather of the two cities: {state['city_1']} and {state['city_2']}."
            "Choose the city with the better weather."
            "Use the weather summaries provided: \n\n - {city_1_weather} \n - {city_2_weather}"
        )

        # Use the model directly for comparison
        messages = [{"role": "user", "content": compare_weather_prompt}]
        
        try:
            result = self.model.invoke(messages, config=get_runnable_config())
            
            # Extract the response content properly
            if hasattr(result, 'content'):
                response_content = result.content
            else:
                response_content = str(result)
                
            state["weather_comparison"] = response_content
            print(f"✅ Weather comparison completed: {response_content[:150]}...")
            logger.info(f"Weather comparison completed: {response_content[:100]}...")
            
        except Exception as e:
            logger.error(f"Error during weather comparison: {e}")
            state["weather_comparison"] = f"Error comparing weather: {str(e)}"
            print(f"❌ Error during weather comparison: {e}")
            
        return state

    def agent_run_tournament(self, state: QueryState) -> QueryState:
        """Let the agent run the entire tournament using tools and reasoning"""
        weather_comparison = state["weather_comparison"]
        victor_city = self._extract_victor_city_structured(weather_comparison)
        
        print(f"\n🏆 TOURNAMENT STARTING!")
        print(f"   Initial victor: {victor_city}")
        print(f"   Agent will now run the tournament using tools...")
        
        logger.info(f"🏆 TOURNAMENT: Initial victor is '{victor_city}' from weather comparison")

        # Create a comprehensive prompt for the agent to run the tournament
        tournament_prompt = f"""
You are a weather tournament organizer. Your task is to find the city with the best weather through a tournament system.

INITIAL SITUATION:
- Current victor: '{victor_city}' (chosen from initial comparison)
- Weather comparison context: {weather_comparison}

YOUR MISSION:
1. First, use the get_challenger_cities tool to get challenger cities that might have better weather than '{victor_city}'
2. Then, run a tournament where you compare the current victor against each challenger using the compare_cities_weather tool
3. For each comparison, use the tool to get an objective comparison
4. Keep track of the current champion as you progress through the tournament
5. At the end, declare the ultimate tournament champion

TOURNAMENT RULES:
- Each round: Current champion vs one challenger
- Use the compare_cities_weather tool for each comparison
- Winner becomes the new champion (or champion defends their title)
- Continue until all challengers have been faced
- Be systematic and use your tools for each comparison

AVAILABLE TOOLS:
- get_challenger_cities(base_city): Get challenger cities
- compare_cities_weather(city1, city2): Compare two cities' weather

Start by using get_challenger_cities to get the challengers, then use compare_cities_weather for each tournament round.
"""

        # Let the agent run the entire tournament
        tournament_result = self.agent_find_better_city.invoke(
            {
                "messages": [
                    {"role": "user", "content": tournament_prompt},
                ]
            },
            config=get_runnable_config(),
        )
        
        # Extract the final result from the agent's conversation
        messages = tournament_result.get("messages", [])
        logger.info(f"🏆 AGENT TOURNAMENT: Agent completed tournament with {len(messages)} messages")
        
        # Log all the agent's messages to see the tool usage
        print(f"\n🏟️ TOURNAMENT AGENT CONVERSATION ({len(messages)} messages):")
        print("=" * 60)
        
        for i, msg in enumerate(messages):
            if hasattr(msg, 'content') and msg.content:
                print(f"\n🤖 AGENT MESSAGE {i+1}:")
                print(f"   {msg.content}")
                logger.info(f"🤖 AGENT MESSAGE {i+1}: {msg.content[:200]}...")
            
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    print(f"\n🔧 TOOL CALL DEBUG:")
                    print(f"   Raw tool_call: {tool_call}")
                    print(f"   Type: {type(tool_call)}")
                    
                    if isinstance(tool_call, dict):
                        # Check for different tool call formats
                        if 'function' in tool_call:
                            # LangChain format: {'function': {'name': '...', 'arguments': {...}}}
                            tool_name = tool_call.get('function', {}).get('name', 'unknown')
                            tool_args = tool_call.get('function', {}).get('arguments', {})
                        else:
                            # Direct format: {'name': '...', 'args': {...}}
                            tool_name = tool_call.get('name', 'unknown')
                            tool_args = tool_call.get('args', {})
                    else:
                        # Handle different tool call formats
                        tool_name = getattr(tool_call, 'name', 'unknown')
                        tool_args = getattr(tool_call, 'args', {})
                    
                    print(f"🔧 TOOL CALL: {tool_name}")
                    print(f"   Arguments: {tool_args}")
                    logger.info(f"🔧 TOOL CALL: {tool_name} with args: {tool_args}")
            
            if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                print(f"\n🔧 TOOL RESULT:")
                print(f"   {msg.content}")
                logger.info(f"🔧 TOOL RESULT: {msg.content[:200]}...")
        
        print("\n" + "=" * 60)
        
        # Log the agent's final response
        if messages:
            final_response = messages[-1].content
            print(f"\n🏆 TOURNAMENT CHAMPION: {final_response}")
            logger.info(f"🏆 TOURNAMENT CHAMPION: {final_response}")
            
            # Extract the actual tournament champion from the agent's response
            tournament_champion = self._extract_tournament_champion(final_response)
            if tournament_champion:
                print(f"🎯 Extracted tournament champion: {tournament_champion}")
                state["better_city"] = tournament_champion
                state["final_victor"] = tournament_champion
            else:
                print(f"⚠️ Could not extract tournament champion, using initial victor: {victor_city}")
                state["better_city"] = victor_city
                state["final_victor"] = victor_city
        else:
            print(f"⚠️ No agent response, using initial victor: {victor_city}")
            state["better_city"] = victor_city
            state["final_victor"] = victor_city
        
        state["tournament_results"] = [{"agent_response": messages[-1].content if messages else "No response"}]
        
        return state

    def _parse_challenger_cities(self, tool_response: str) -> list[str]:
        """Parse challenger cities from tool response"""
        # Look for the pattern "Challenger cities that might have better weather than X: city1, city2, city3"
        if "Challenger cities that might have better weather than" in tool_response:
            # Extract the part after the colon
            cities_part = tool_response.split(":")[-1].strip()
            # Split by comma and clean up
            cities = [city.strip() for city in cities_part.split(",")]
            return cities
        else:
            # Fallback: try to extract city names from the response
            logger.warning(f"Could not parse challenger cities from: {tool_response}")
            return []

    def _extract_tournament_champion(self, response: str) -> str:
        """Extract the tournament champion from the agent's final response"""
        import re
        
        # Look for patterns like "The ultimate tournament champion is X"
        champion_patterns = [
            r"ultimate tournament champion is ([^.]+)",
            r"tournament champion is ([^.]+)",
            r"champion is ([^.]+)",
            r"winner is ([^.]+)",
            r"victor is ([^.]+)"
        ]
        
        for pattern in champion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                champion = match.group(1).strip()
                # Clean up the champion name (remove trailing punctuation)
                champion = re.sub(r'[.,!?]+$', '', champion).strip()
                return champion
        
        # If no pattern matches, try to find city names in the response
        # Look for common city names that might be mentioned
        city_names = [
            "San Diego", "Dubai", "Tel Aviv", "Athens", "Haifa", "Doha", "Perth", 
            "Lisbon", "Barcelona", "Sydney", "Cape Town", "Boston", "New York"
        ]
        
        for city in city_names:
            if city.lower() in response.lower():
                return city
        
        return None

    def _extract_city_name_from_response(self, response: str, city1: str, city2: str) -> str:
        """Extract the winning city name from agent response"""
        response_lower = response.lower()
        city1_lower = city1.lower()
        city2_lower = city2.lower()
        
        # Check for the new LLM format first
        if "WINNER:" in response:
            # Extract the winner from the structured format
            import re
            winner_match = re.search(r"WINNER:\s*([^\n]+)", response, re.IGNORECASE)
            if winner_match:
                winner = winner_match.group(1).strip()
                # Check if the winner matches one of our cities
                if city1_lower in winner.lower():
                    return city1
                elif city2_lower in winner.lower():
                    return city2
                else:
                    # Winner doesn't match either city, try to find the closest match
                    if city1_lower in response_lower:
                        return city1
                    elif city2_lower in response_lower:
                        return city2
        
        # Fallback to original logic for non-structured responses
        if city1_lower in response_lower and city2_lower in response_lower:
            # Both cities mentioned - look for patterns that indicate winner
            if "better" in response_lower or "wins" in response_lower or "victor" in response_lower:
                # Look for which city comes after "better" or similar words
                import re
                # Pattern: "city1 has better weather" or "city1 is better"
                better_patterns = [
                    rf"{city1_lower}.*better",
                    rf"{city2_lower}.*better",
                    rf"better.*{city1_lower}",
                    rf"better.*{city2_lower}",
                ]
                
                for pattern in better_patterns:
                    if re.search(pattern, response_lower):
                        if city1_lower in pattern:
                            return city1
                        elif city2_lower in pattern:
                            return city2
                
                # If no clear pattern, check word order
                city1_pos = response_lower.find(city1_lower)
                city2_pos = response_lower.find(city2_lower)
                
                if city1_pos < city2_pos:
                    return city1
                else:
                    return city2
            else:
                # No clear winner indication, default to first city
                return city1
        elif city1_lower in response_lower:
            return city1
        elif city2_lower in response_lower:
            return city2
        else:
            # Neither city found, default to first city
            logger.warning(f"Could not extract city name from: {response}")
            return city1

    def _extract_victor_city_structured(self, weather_comparison: str) -> str:
        """Extract the victor city using structured LLM response"""
        extraction_prompt = (
            f"Analyze this weather comparison and identify which city was chosen as the victor/winner:\n\n"
            f"{weather_comparison}\n\n"
            f"Extract the city name that was determined to have better weather. "
            f"Return only the city name, not any additional text."
        )
        
        try:
            structured_llm = self.model.with_structured_output(VictorCityResponse)
            response = structured_llm.invoke(
                [{"role": "user", "content": extraction_prompt}],
                config=get_runnable_config()
            )
            logger.debug(f"Extracted victor city: '{response.victor_city}' with reasoning: {response.reasoning}")
            return response.victor_city
        except Exception as e:
            logger.error(f"Failed to extract victor city using structured response: {e}")
            # Fallback: return the first city mentioned in the comparison
            return "Unknown"





def query_llm(city_1: str, city_2: str):
    """Query the llm for weather information within a workflow"""
    print(f"\n🚀 STARTING WEATHER TOURNAMENT SYSTEM")
    print(f"   Cities: {city_1} vs {city_2}")
    print(f"   System will: Get weather → Compare → Run agent tournament")
    print("=" * 60)
    
    logger.info(f"Starting weather query workflow for cities: {city_1} and {city_2}")

    workflow = QueryWorkflow()
    initial_state = {
        "city_1": city_1,
        "city_2": city_2,
        "city_1_weather": "",
        "city_2_weather": "",
        "better_city": "",
        "weather_comparison": "",
        "challenger_cities": [],
        "tournament_results": [],
        "final_victor": "",
        "messages": [],
        "remaining_steps": 5
    }

    result = workflow.graph.invoke(initial_state, config=get_runnable_config())
    
    print(f"\n🎉 WEATHER TOURNAMENT COMPLETED!")
    print(f"   Final champion: {result.get('final_victor', 'Unknown')}")
    print("=" * 60)
    
    logger.info("Weather query completed successfully!")
    return result

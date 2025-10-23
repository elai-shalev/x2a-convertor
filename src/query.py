import structlog


from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from langgraph.prebuilt import create_react_agent
from tools.weather_tools import search_city_with_better_weather


from typing import TypedDict
from src.model import get_model, get_runnable_config


logger = structlog.get_logger(__name__)

class QueryResponse(BaseModel):
    """Structured output for query response"""

    response: str


class QueryState(TypedDict):
    city_1: str
    city_2: str
    city_1_weather: str
    city_2_weather: str
    better_city: str
    weather_comparison: str
    messages: list[dict[str, str]]
    remaining_steps: int


class QueryWorkflow:
    def __init__(self, model=None) -> None:
        self.model = model or get_model()
        self.graph = self._build_graph()
        self.agent_find_better_city = self._build_agent_find_better_city()
        print(self.graph.get_graph().draw_mermaid())

    def _build_agent_find_better_city(self):
        """Create a LangGraph agent with that compares cities' weather"""
        logger.info("Creating grading agent")

        tools = [
            search_city_with_better_weather,
        ]

        # Create the agent with higher recursion limit
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
        workflow.add_node("agent_find_better_city", lambda state: self.node_agent_find_better_city(state))

        workflow.set_entry_point("query_city_1_weather")
        workflow.add_edge("query_city_1_weather", "query_city_2_weather")
        workflow.add_edge("query_city_2_weather", "compare_weather")
        workflow.add_edge("compare_weather", "agent_find_better_city")
        workflow.add_edge("agent_find_better_city", END)

        return workflow.compile()

    def weather_query(self, state: QueryState, city_number: int) -> QueryState:
        """Query the llm for weather information for a given city"""
        if city_number == 1:
            city = state["city_1"]
        else:
            city = state["city_2"]
        
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
        return state
    
    def compare_weather(self, state: QueryState) -> QueryState:
        """Compare the weather of the two cities"""
        city_1_weather = state["city_1_weather"]
        city_2_weather = state["city_2_weather"]

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
            logger.info(f"Weather comparison completed: {response_content[:100]}...")
            
        except Exception as e:
            logger.error(f"Error during weather comparison: {e}")
            state["weather_comparison"] = f"Error comparing weather: {str(e)}"
            
        return state

    def node_agent_find_better_city(self, state: QueryState) -> QueryState:
        """Find the city with the better weather"""
        weather_comparison = state["weather_comparison"]

        # Create the message content
        message_content = (
            f"Find a city that likely has better weather than the city depicted as the victor in the weather comparison report. "
            f"The weather comparison report is given here: {weather_comparison}. "
            "You can use your tools to research. Return only the city name."
        )

        # For Vertex AI compatibility, we need to ensure the message format is correct
        from langchain_core.messages import HumanMessage
        
        # Create a proper HumanMessage object
        message = HumanMessage(content=message_content)
        
        # The agent expects a dict with 'messages' and any other state keys
        agent_input = {
            "messages": [message],
            **state,  # include any existing keys (like city_1, city_2, etc.)
        }

        try:
            # Run the agent
            agent_result = self.agent_find_better_city.invoke(agent_input, config=get_runnable_config())

            # agent_result is itself a state dict — so extract what you need from it
            final_message = agent_result["messages"][-1]["content"]
            state["better_city"] = final_message
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            # Fallback: just return a simple response
            state["better_city"] = "Unable to find a better city due to API error"

        return state  # ✅ must return dict


def query_llm(city_1: str, city_2: str):
    """Query the llm for weather information within a workflow"""
    logger.info(f"Starting weather query workflow for cities: {city_1} and {city_2}")

    workflow = QueryWorkflow()
    initial_state = {
        "city_1": city_1,
        "city_2": city_2,
        "city_1_weather": "",
        "city_2_weather": "",
        "better_city": "",
        "weather_comparison": "",
        "messages": [],
        "remaining_steps": 5
    }

    result = workflow.graph.invoke(initial_state, config=get_runnable_config())
    logger.info("Weather query completed successfully!")
    print(f"Weather comparison for {city_1} and {city_2}:")
    print(result["weather_comparison"])
    return result

"""
SQL Query Agent - Refactored with object-oriented design.
"""

from typing import Annotated, TypedDict, List, Tuple
from operator import add
import logging

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_sql_query_chain
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_core.messages import HumanMessage, AIMessage

from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Send, interrupt
from langgraph.checkpoint.memory import InMemorySaver

from config import ConfigManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryOutput(TypedDict):
    """Generated SQL query output schema."""
    query: Annotated[str, ..., "Syntactically valid SQL query."]
    suggestion: Annotated[list[str], ..., "Suggestion scheme improvement to improve the scheme performance"]


class State(MessagesState):
    """State management for the SQL Query Agent workflow."""
    user_request: str
    user_feedback: str
    selected_query: str
    query_suggestion: Annotated[List[Tuple[str, dict]], add]
    refactoring_suggestion: str
    query_result: object
    error_message: str


class DatabaseManager:
    """Database connection and query management."""
    
    def __init__(self, config: ConfigManager):
        """Initialize database manager."""
        self.config = config
        self._db = None
        self._query_tool = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection."""
        try:
            self._db = SQLDatabase.from_uri(self.config.database.uri)
            self._query_tool = QuerySQLDatabaseTool(db=self._db)
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @property
    def db(self) -> SQLDatabase:
        """Get database instance."""
        return self._db
    
    @property
    def dialect(self) -> str:
        """Get database dialect."""
        return self._db.dialect
    
    @property
    def usable_tables(self) -> list[str]:
        """Get usable table names."""
        return self._db.get_usable_table_names()
    
    def execute_query(self, query: str) -> str:
        """Execute SQL query."""
        try:
            return self._query_tool.invoke(query)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise


class LLMManager:
    """LLM management for different query generation strategies."""
    
    def __init__(self, config: ConfigManager):
        """Initialize LLM manager."""
        self.config = config
        self._initialize_llms()
    
    def _initialize_llms(self):
        """Initialize LLM instances."""
        try:
            self.smart_llm = ChatOpenAI(
                model_name=self.config.llm.smart_model,
                temperature=self.config.llm.temperature_smart
            )
            self.query_llm = ChatOpenAI(
                model_name=self.config.llm.query_model,
                temperature=self.config.llm.temperature_query
            )
            logger.info("LLMs initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLMs: {e}")
            raise
    
    def get_structured_output_llm(self) -> ChatOpenAI:
        """Get LLM with structured output for QueryOutput."""
        return self.query_llm.with_structured_output(QueryOutput)


class QueryChainManager:
    """Management of different query generation chains."""
    
    def __init__(self, config: ConfigManager, db_manager: DatabaseManager, llm_manager: LLMManager):
        """Initialize query chain manager."""
        self.config = config
        self.db_manager = db_manager
        self.llm_manager = llm_manager
        self.entity_relationship = config.load_erd()
        self._initialize_chains()
    
    def _initialize_chains(self):
        """Initialize query generation chains."""
        try:
            # Create prompts
            self.basic_prompt = ChatPromptTemplate.from_messages([
                ("system", self.config.load_prompt("basic_sql_agent.template")),
                ("user", "Question: {input}"),
            ])
            
            self.optimized_prompt = ChatPromptTemplate.from_messages([
                ("system", self.config.load_prompt("optimized_sql_agent.template")),
                ("user", "Question: {input}"),
            ])
            
            self.advanced_prompt = ChatPromptTemplate.from_messages([
                ("system", self.config.load_prompt("advanced_sql_agent.template")),
                ("user", "Question: {input}"),
            ])
            
            # Create chains
            structured_llm = self.llm_manager.get_structured_output_llm()
            
            self.basic_chain = (
                create_sql_query_chain(
                    llm=self.llm_manager.query_llm,
                    db=self.db_manager.db,
                    prompt=self.basic_prompt
                ) | structured_llm
            )
            
            self.optimized_chain = (
                create_sql_query_chain(
                    llm=self.llm_manager.query_llm,
                    db=self.db_manager.db,
                    prompt=self.optimized_prompt
                ) | structured_llm
            )
            
            self.advanced_chain = (
                create_sql_query_chain(
                    llm=self.llm_manager.smart_llm,
                    db=self.db_manager.db,
                    prompt=self.advanced_prompt
                ) | structured_llm
            )
            
            logger.info("Query chains initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize query chains: {e}")
            raise
    
    def get_query_params(self, user_request: str, user_feedback: str) -> dict:
        """Get common parameters for query generation."""
        return {
            "dialect": self.db_manager.dialect,
            "top_k": 5,
            "table_info": self.db_manager.usable_tables,
            "entity_relationship": self.entity_relationship,
            "question": user_request,
            "user_feedback": user_feedback
        }


class WorkflowManager:
    """Management of workflow nodes and logic."""
    
    def __init__(self, db_manager: DatabaseManager, chain_manager: QueryChainManager):
        """Initialize workflow manager."""
        self.db_manager = db_manager
        self.chain_manager = chain_manager
    
    def gateway(self, state: State) -> dict:
        """Gateway node - reset state."""
        return {
            "selected_query": None,
            "query_suggestion": [],
            "refactoring_suggestion": None,
            "query_result": None,
            "error_message": None,
        }
    
    def generate_query(self, state: State) -> list[Send]:
        """Generate query tasks for all agents."""
        return [
            Send("query_agent_1", {
                "user_request": state["user_request"],
                "user_feedback": state["user_feedback"]
            }),
            Send("query_agent_2", {
                "user_request": state["user_request"],
                "user_feedback": state["user_feedback"]
            }),
            Send("query_agent_3", {
                "user_request": state["user_request"],
                "user_feedback": state["user_feedback"]
            })
        ]
    
    def find_selected_query(self, state: State, agent_name: str) -> str:
        """Find selected query by agent name."""
        for agent, query_data in state["query_suggestion"]:
            if agent == agent_name:
                return query_data["query"]
        return None
    
    def find_suggestion(self, state: State, agent_name: str) -> list[str]:
        """Find suggestions by agent name."""
        for agent, query_data in state["query_suggestion"]:
            if agent == agent_name:
                return query_data.get("suggestion", [])
        return []
    
    def wait_user_feedback(self, state: State) -> dict:
        """Wait for user feedback with interrupt."""
        user_input = interrupt({
            "action": "wait_user_feedback",
            "query_suggestions": state["query_suggestion"],
            "question": [
                "무엇을 실행할까요?",
                "1, 2, 3 중 하나를 입력하면 해당 쿼리를 실행합니다.",
                "stop, cancel, exit, quit 중 하나를 입력하면 쿼리 실행을 중단합니다.",
                "쿼리 수정을 원하면 피드백을 입력하세요."
            ]
        })
        
        if user_input == "1":
            return {
                "user_feedback": "1",
                "selected_query": self.find_selected_query(state, "query_agent_1")
            }
        elif user_input == "2":
            return {
                "user_feedback": "2",
                "selected_query": self.find_selected_query(state, "query_agent_2")
            }
        elif user_input == "3":
            return {
                "user_feedback": "3",
                "selected_query": self.find_selected_query(state, "query_agent_3"),
                "refactoring_suggestion": self.find_suggestion(state, "query_agent_3")
            }
        
        return {"user_feedback": user_input}
    
    def next_after_feedback(self, state: State) -> str:
        """Determine next action after feedback."""
        user_input = state["user_feedback"]
        if user_input in ["1", "2", "3"]:
            return "execute"
        elif user_input in ["stop", "cancel", "exit", "quit"]:
            return "cancel"
        return "retry"
    
    def execute_query(self, state: State) -> dict:
        """Execute selected query."""
        selected_query = state["selected_query"]
        
        try:
            query_result = self.db_manager.execute_query(selected_query)
            return {"query_result": query_result, "error_message": None}
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {"query_result": None, "error_message": str(e)}
    
    def query_agent_1(self, state: State) -> dict:
        """Basic query agent."""
        try:
            params = self.chain_manager.get_query_params(
                state["user_request"], state["user_feedback"]
            )
            response = self.chain_manager.basic_chain.invoke(params)
            return {"query_suggestion": [("query_agent_1", {"query": response["query"]})]}
        except Exception as e:
            logger.error(f"Query agent 1 failed: {e}")
            return {"query_suggestion": [("query_agent_1", {"query": f"-- Error: {e}"})]}
    
    def query_agent_2(self, state: State) -> dict:
        """Optimized query agent."""
        try:
            params = self.chain_manager.get_query_params(
                state["user_request"], state["user_feedback"]
            )
            response = self.chain_manager.optimized_chain.invoke(params)
            return {"query_suggestion": [("query_agent_2", {"query": response["query"]})]}
        except Exception as e:
            logger.error(f"Query agent 2 failed: {e}")
            return {"query_suggestion": [("query_agent_2", {"query": f"-- Error: {e}"})]}
    
    def query_agent_3(self, state: State) -> dict:
        """Advanced query agent."""
        try:
            params = self.chain_manager.get_query_params(
                state["user_request"], state["user_feedback"]
            )
            response = self.chain_manager.advanced_chain.invoke(params)
            return {
                "query_suggestion": [(
                    "query_agent_3",
                    {
                        "query": response["query"],
                        "suggestion": response["suggestion"]
                    }
                )]
            }
        except Exception as e:
            logger.error(f"Query agent 3 failed: {e}")
            return {
                "query_suggestion": [(
                    "query_agent_3",
                    {
                        "query": f"-- Error: {e}",
                        "suggestion": []
                    }
                )]
            }
    
    def aggregate(self, state: State) -> dict:
        """Aggregate results from all agents."""
        return {}
    
    def end_on_success(self, state: State) -> dict:
        """End workflow on successful query execution."""
        messages = [
            AIMessage(content="쿼리 실행 완료"),
            AIMessage(content=str(state["query_result"]))
        ]
        
        if state.get("refactoring_suggestion"):
            messages.append(AIMessage(content=str(state["refactoring_suggestion"])))
        
        return {"messages": messages}
    
    def end_on_error(self, state: State) -> dict:
        """End workflow on error."""
        return {
            "messages": [
                AIMessage(content="쿼리 실행 오류"),
                AIMessage(content=str(state["error_message"]))
            ]
        }
    
    def end_on_cancel(self, state: State) -> dict:
        """End workflow on cancellation."""
        return {"messages": [AIMessage(content="쿼리 실행 취소")]}


class SQLQueryAgent:
    """Main SQL Query Agent class."""
    
    def __init__(self, config: ConfigManager = None):
        """Initialize SQL Query Agent."""
        self.config = config or ConfigManager()
        self._initialize_components()
        self._build_graph()
    
    def _initialize_components(self):
        """Initialize all components."""
        try:
            self.db_manager = DatabaseManager(self.config)
            self.llm_manager = LLMManager(self.config)
            self.chain_manager = QueryChainManager(self.config, self.db_manager, self.llm_manager)
            self.workflow_manager = WorkflowManager(self.db_manager, self.chain_manager)
            logger.info("All components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _build_graph(self):
        """Build the workflow graph."""
        try:
            builder = StateGraph(State)
            
            # Add nodes
            builder.add_node("gateway", self.workflow_manager.gateway)
            builder.add_node("wait_user_feedback", self.workflow_manager.wait_user_feedback)
            builder.add_node("execute_query", self.workflow_manager.execute_query)
            builder.add_node("query_agent_1", self.workflow_manager.query_agent_1)
            builder.add_node("query_agent_2", self.workflow_manager.query_agent_2)
            builder.add_node("query_agent_3", self.workflow_manager.query_agent_3)
            builder.add_node("aggregate", self.workflow_manager.aggregate)
            builder.add_node("end_on_success", self.workflow_manager.end_on_success)
            builder.add_node("end_on_error", self.workflow_manager.end_on_error)
            builder.add_node("end_on_cancel", self.workflow_manager.end_on_cancel)
            
            # Add edges
            builder.add_edge(START, "gateway")
            builder.add_conditional_edges(
                "gateway",
                self.workflow_manager.generate_query,
                ["query_agent_1", "query_agent_2", "query_agent_3"]
            )
            builder.add_edge("query_agent_1", "aggregate")
            builder.add_edge("query_agent_2", "aggregate")
            builder.add_edge("query_agent_3", "aggregate")
            builder.add_edge("aggregate", "wait_user_feedback")
            builder.add_conditional_edges(
                "wait_user_feedback",
                self.workflow_manager.next_after_feedback,
                {
                    "retry": "gateway",
                    "execute": "execute_query",
                    "cancel": "end_on_cancel"
                }
            )
            builder.add_conditional_edges(
                "execute_query",
                lambda x: "success" if x["error_message"] is None else "error",
                {
                    "success": "end_on_success",
                    "error": "end_on_error",
                }
            )
            builder.add_edge("end_on_success", END)
            builder.add_edge("end_on_error", END)
            builder.add_edge("end_on_cancel", END)
            
            # Compile graph
            checkpointer = InMemorySaver()
            self.graph = builder.compile(checkpointer=checkpointer)
            logger.info("Workflow graph built successfully")
        except Exception as e:
            logger.error(f"Failed to build graph: {e}")
            raise
    
    def get_graph(self):
        """Get the compiled workflow graph."""
        return self.graph
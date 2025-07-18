"""
Configuration management module for SQL Query Agent.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Database configuration."""
    hostname: str
    port: int
    database: str
    username: str
    password: str
    
    @property
    def uri(self) -> str:
        """Generate database URI."""
        return f"mysql+pymysql://{self.username}:{self.password}@{self.hostname}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """LLM configuration."""
    smart_model: str = "gpt-4.1"
    query_model: str = "gpt-4.1-mini"
    temperature_smart: float = 0.0
    temperature_query: float = 0.2


@dataclass
class ProjectConfig:
    """Project configuration."""
    project_dir: str
    resource_dir: str
    prompt_dir: str
    erd_filename: str = "ERD.md"
    
    @property
    def erd_path(self) -> str:
        """Get ERD file path."""
        return os.path.join(self.resource_dir, self.erd_filename)


class ConfigManager:
    """Configuration manager for the SQL Query Agent."""
    
    def __init__(self):
        """Initialize configuration manager."""
        load_dotenv()
        self._load_configurations()
    
    def _load_configurations(self):
        """Load all configurations."""
        self.database = self._load_database_config()
        self.llm = self._load_llm_config()
        self.project = self._load_project_config()
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment variables."""
        return DatabaseConfig(
            hostname=os.getenv("MYSQL_HOSTNAME", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE", "test"),
            username=os.getenv("MYSQL_USERNAME", "user"),
            password=os.getenv("MYSQL_PASSWORD", "1234")
        )
    
    def _load_llm_config(self) -> LLMConfig:
        """Load LLM configuration."""
        return LLMConfig(
            smart_model=os.getenv("LLM_SMART_MODEL", "gpt-4.1"),
            query_model=os.getenv("LLM_QUERY_MODEL", "gpt-4.1-mini"),
            temperature_smart=float(os.getenv("LLM_TEMPERATURE_SMART", "0.0")),
            temperature_query=float(os.getenv("LLM_TEMPERATURE_QUERY", "0.2"))
        )
    
    def _load_project_config(self) -> ProjectConfig:
        """Load project configuration."""
        project_dir = os.getenv("PROJECT_DIR", os.getcwd())
        resource_dir = os.path.join(project_dir, "resource")
        prompt_dir = os.path.join(resource_dir, "prompt")
        
        return ProjectConfig(
            project_dir=project_dir,
            resource_dir=resource_dir,
            prompt_dir=prompt_dir,
            erd_filename=os.getenv("ERD_FILENAME", "ERD.md")
        )
    
    def get_prompt_path(self, prompt_filename: str) -> str:
        """Get prompt file path."""
        return os.path.join(self.project.prompt_dir, prompt_filename)
    
    def load_prompt(self, prompt_filename: str) -> str:
        """Load prompt from file."""
        prompt_path = self.get_prompt_path(prompt_filename)
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    def load_erd(self) -> list[str]:
        """Load ERD file content."""
        try:
            with open(self.project.erd_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            raise FileNotFoundError(f"ERD file not found: {self.project.erd_path}") 
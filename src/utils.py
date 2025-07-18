"""
Utilities module for SQL Query Agent.
"""

import logging
import functools
import traceback
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    """Error types for categorization."""
    DATABASE_ERROR = "database_error"
    LLM_ERROR = "llm_error"
    WORKFLOW_ERROR = "workflow_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """Error information container."""
    error_type: ErrorType
    message: str
    details: Optional[str] = None
    user_message: Optional[str] = None


class ErrorHandler:
    """Error handling utilities."""
    
    ERROR_MESSAGES = {
        ErrorType.DATABASE_ERROR: {
            "default": "데이터베이스 연결 또는 쿼리 실행 중 오류가 발생했습니다.",
            "connection": "데이터베이스 연결에 실패했습니다. 설정을 확인해주세요.",
            "query": "SQL 쿼리 실행 중 오류가 발생했습니다."
        },
        ErrorType.LLM_ERROR: {
            "default": "AI 모델 호출 중 오류가 발생했습니다.",
            "api_key": "OpenAI API 키가 유효하지 않습니다.",
            "quota": "API 사용량이 초과되었습니다."
        },
        ErrorType.WORKFLOW_ERROR: {
            "default": "워크플로우 처리 중 오류가 발생했습니다.",
            "state": "워크플로우 상태 관리 중 오류가 발생했습니다."
        },
        ErrorType.VALIDATION_ERROR: {
            "default": "입력값 검증 중 오류가 발생했습니다.",
            "empty": "입력값이 비어있습니다.",
            "invalid": "유효하지 않은 입력값입니다."
        },
        ErrorType.CONFIGURATION_ERROR: {
            "default": "설정 파일 로드 중 오류가 발생했습니다.",
            "missing": "필수 설정이 누락되었습니다.",
            "invalid": "설정값이 유효하지 않습니다."
        },
        ErrorType.UNKNOWN_ERROR: {
            "default": "알 수 없는 오류가 발생했습니다."
        }
    }
    
    @classmethod
    def categorize_error(cls, error: Exception) -> ErrorType:
        """Categorize error by type."""
        error_str = str(error).lower()
        
        # Database errors
        if any(keyword in error_str for keyword in ['mysql', 'database', 'connection', 'sql']):
            return ErrorType.DATABASE_ERROR
        
        # LLM errors
        if any(keyword in error_str for keyword in ['openai', 'api', 'token', 'model']):
            return ErrorType.LLM_ERROR
        
        # Workflow errors
        if any(keyword in error_str for keyword in ['workflow', 'state', 'interrupt']):
            return ErrorType.WORKFLOW_ERROR
        
        # Validation errors
        if any(keyword in error_str for keyword in ['validation', 'invalid', 'empty']):
            return ErrorType.VALIDATION_ERROR
        
        # Configuration errors
        if any(keyword in error_str for keyword in ['config', 'setting', 'file not found']):
            return ErrorType.CONFIGURATION_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    @classmethod
    def get_user_message(cls, error: Exception, error_type: ErrorType = None) -> str:
        """Get user-friendly error message."""
        if error_type is None:
            error_type = cls.categorize_error(error)
        
        error_str = str(error).lower()
        messages = cls.ERROR_MESSAGES[error_type]
        
        # Try to find specific message
        for keyword, message in messages.items():
            if keyword != "default" and keyword in error_str:
                return message
        
        return messages["default"]
    
    @classmethod
    def create_error_info(cls, error: Exception, context: str = None) -> ErrorInfo:
        """Create error information."""
        error_type = cls.categorize_error(error)
        user_message = cls.get_user_message(error, error_type)
        
        details = f"Context: {context}\n" if context else ""
        details += f"Error: {str(error)}\n"
        details += f"Traceback: {traceback.format_exc()}"
        
        return ErrorInfo(
            error_type=error_type,
            message=str(error),
            details=details,
            user_message=user_message
        )


class LoggerManager:
    """Logger management utilities."""
    
    @staticmethod
    def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """Setup logger with consistent formatting."""
        logger = logging.getLogger(name)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(level)
        
        return logger
    
    @staticmethod
    def log_error(logger: logging.Logger, error: Exception, context: str = None):
        """Log error with context."""
        error_info = ErrorHandler.create_error_info(error, context)
        logger.error(f"Error in {context}: {error_info.message}")
        logger.debug(f"Error details: {error_info.details}")


def handle_exceptions(error_type: ErrorType = None, context: str = None):
    """Decorator for handling exceptions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = LoggerManager.setup_logger(func.__module__)
                LoggerManager.log_error(logger, e, context or func.__name__)
                
                error_info = ErrorHandler.create_error_info(e, context)
                if error_type:
                    error_info.error_type = error_type
                
                raise e
        return wrapper
    return decorator


class Validator:
    """Input validation utilities."""
    
    @staticmethod
    def validate_non_empty(value: str, field_name: str = "Input") -> bool:
        """Validate that value is not empty."""
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty")
        return True
    
    @staticmethod
    def validate_database_uri(uri: str) -> bool:
        """Validate database URI format."""
        if not uri.startswith(('mysql://', 'mysql+pymysql://')):
            raise ValueError("Database URI must start with 'mysql://' or 'mysql+pymysql://'")
        return True
    
    @staticmethod
    def validate_workflow_state(state: str) -> bool:
        """Validate workflow state."""
        valid_states = ['waiting_for_question', 'processing', 'waiting_for_feedback']
        if state not in valid_states:
            raise ValueError(f"Invalid workflow state: {state}")
        return True


class SafeExecutor:
    """Safe execution utilities with error handling."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize safe executor."""
        self.logger = logger or LoggerManager.setup_logger(__name__)
    
    def execute_with_retry(self, func: Callable, max_retries: int = 3, 
                          delay: float = 1.0, context: str = None) -> Any:
        """Execute function with retry logic."""
        import time
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    LoggerManager.log_error(self.logger, e, context)
                    raise
                
                self.logger.warning(f"Attempt {attempt + 1} failed in {context}: {str(e)}")
                time.sleep(delay)
        
        return None
    
    def execute_safely(self, func: Callable, default_value: Any = None, 
                      context: str = None) -> Any:
        """Execute function safely with default value on error."""
        try:
            return func()
        except Exception as e:
            LoggerManager.log_error(self.logger, e, context)
            return default_value


class PerformanceMonitor:
    """Performance monitoring utilities."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize performance monitor."""
        self.logger = logger or LoggerManager.setup_logger(__name__)
    
    def time_function(self, func: Callable, context: str = None) -> Callable:
        """Decorator to time function execution."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                self.logger.info(f"{context or func.__name__} executed in {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(f"{context or func.__name__} failed after {execution_time:.2f}s: {str(e)}")
                raise
        return wrapper


def create_safe_dict(data: Dict[str, Any], safe_keys: list[str]) -> Dict[str, Any]:
    """Create a safe dictionary with only specified keys."""
    return {key: data.get(key) for key in safe_keys if key in data}


def sanitize_sql_query(query: str) -> str:
    """Sanitize SQL query for logging (remove sensitive data)."""
    # Remove potential sensitive data patterns
    import re
    
    # Remove string literals that might contain sensitive data
    query = re.sub(r"'[^']*'", "'***'", query)
    query = re.sub(r'"[^"]*"', '"***"', query)
    
    return query 
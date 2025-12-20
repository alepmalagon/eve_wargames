"""
Centralized logging configuration for the EVE Wargames application.

Provides structured logging that works well with both console output (development)
and Docker logs (production). Supports request tracing and proper log formatting.
"""

import logging
import logging.config
import sys
import json
from typing import Dict, Any
from datetime import datetime
import uuid
from contextvars import ContextVar

from .config import settings

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')


class RequestIDFilter(logging.Filter):
    """Add request ID to log records for tracing."""
    
    def filter(self, record):
        record.request_id = request_id_var.get('')
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production environments."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id') and record.request_id:
            log_entry['request_id'] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'request_id']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development environments."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        colored_level = f"{level_color}{record.levelname}{self.COLORS['RESET']}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build the log message
        message = record.getMessage()
        
        # Add request ID if available
        request_id = getattr(record, 'request_id', '')
        request_part = f" [{request_id}]" if request_id else ""
        
        # Format the final message
        formatted = f"{timestamp} | {colored_level:8} | {record.name:20} | {message}{request_part}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)
        
        return formatted


def setup_logging() -> None:
    """
    Configure logging for the application.
    
    Sets up different formatters based on environment:
    - Development: Colored console output
    - Production: JSON structured logging for Docker
    """
    # Determine if we're in development mode
    is_development = settings.DEBUG
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Add request ID filter
    request_filter = RequestIDFilter()
    console_handler.addFilter(request_filter)
    
    # Set formatter based on environment
    if is_development:
        formatter = ColoredConsoleFormatter()
    else:
        formatter = JSONFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_loggers()
    
    # Log the logging setup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Level: {settings.LOG_LEVEL}, "
        f"Format: {'Console' if is_development else 'JSON'}"
    )


def configure_loggers() -> None:
    """Configure specific loggers for different components."""
    
    # Set levels for third-party libraries
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    # Application loggers
    logging.getLogger('app').setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: str = None) -> str:
    """
    Set the request ID for the current context.
    
    Args:
        request_id: Request ID to set. If None, generates a new UUID.
        
    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]  # Short UUID for readability
    
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get('')


def clear_request_id() -> None:
    """Clear the request ID from context."""
    request_id_var.set('')


# Convenience function to get application loggers
def get_app_logger(module_name: str) -> logging.Logger:
    """
    Get an application logger with consistent naming.
    
    Args:
        module_name: Module name (typically __name__)
        
    Returns:
        Logger instance with app prefix
    """
    # Remove 'app.' prefix if already present to avoid duplication
    if module_name.startswith('app.'):
        module_name = module_name[4:]
    
    return get_logger(f'app.{module_name}')

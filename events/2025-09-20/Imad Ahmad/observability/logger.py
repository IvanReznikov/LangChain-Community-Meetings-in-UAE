import structlog
import logging
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class DatabaseHandler(logging.Handler):
    """Custom logging handler that stores logs in SQLite database."""
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                request_id TEXT,
                tool_name TEXT,
                duration_ms INTEGER,
                inputs_hash TEXT,
                output_size INTEGER,
                status TEXT,
                extra_data TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def emit(self, record):
        """Emit a log record to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract structured data from the record
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 
                              'exc_text', 'stack_info']:
                    extra_data[key] = value
            
            cursor.execute("""
                INSERT INTO logs (timestamp, level, message, request_id, tool_name, 
                                duration_ms, inputs_hash, output_size, status, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.fromtimestamp(record.created).isoformat(),
                record.levelname,
                record.getMessage(),
                getattr(record, 'request_id', None),
                getattr(record, 'tool_name', None),
                getattr(record, 'duration_ms', None),
                getattr(record, 'inputs_hash', None),
                getattr(record, 'output_size', None),
                getattr(record, 'status', None),
                json.dumps(extra_data) if extra_data else None
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to log to database: {e}")


def setup_logger(db_path: str = "data/travel_assistant.db") -> structlog.stdlib.BoundLogger:
    """Set up structured logging with database storage."""
    
    # Ensure data directory exists
    Path(db_path).parent.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up Python logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=logging.INFO,
    )
    
    # Add database handler
    logger = logging.getLogger()
    db_handler = DatabaseHandler(db_path)
    logger.addHandler(db_handler)
    
    return structlog.get_logger()


def log_tool_call(logger: structlog.stdlib.BoundLogger, 
                  tool_name: str, 
                  inputs: Dict[str, Any], 
                  request_id: str) -> str:
    """Log the start of a tool call."""
    inputs_hash = str(hash(str(sorted(inputs.items()))))
    
    logger.info(
        "Tool call started",
        tool_name=tool_name,
        request_id=request_id,
        inputs_hash=inputs_hash,
        status="started"
    )
    
    return inputs_hash


def log_tool_result(logger: structlog.stdlib.BoundLogger,
                   tool_name: str,
                   inputs_hash: str,
                   result: Any,
                   duration_ms: int,
                   request_id: str,
                   success: bool = True):
    """Log the result of a tool call."""
    output_size = len(str(result)) if result else 0
    status = "succeeded" if success else "failed"
    
    logger.info(
        "Tool call completed",
        tool_name=tool_name,
        request_id=request_id,
        inputs_hash=inputs_hash,
        output_size=output_size,
        duration_ms=duration_ms,
        status=status
    )


def log_trace(logger: structlog.stdlib.BoundLogger,
              request_id: str,
              event_type: str,
              data: Dict[str, Any]):
    """Log a trace event."""
    # Also store in traces table
    db_path = "data/travel_assistant.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO traces (request_id, timestamp, event_type, data)
            VALUES (?, ?, ?, ?)
        """, (
            request_id,
            datetime.now().isoformat(),
            event_type,
            json.dumps(data)
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to store trace", error=str(e))
    
    logger.info(
        "Trace event",
        request_id=request_id,
        event_type=event_type,
        **data
    )

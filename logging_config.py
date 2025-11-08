import logging
import time
import uuid
from logging.handlers import TimedRotatingFileHandler
from flask import request, session, g

"""Central logging utilities for all Flask apps/blueprints.

Features:
- Daily rotating file handler with retention (backup_count)
- Console handler
- Per-request logging with skip filters for static/assets/blueprints/endpoints
- Stable session identifier (sid) + per-request identifier (rid)

Log line format (normal):
  REQ app=<app_name> sid=<session_id> rid=<request_id> user=<user_or_-> method=<METHOD> path=<PATH> status=<CODE> dur_ms=<ms> ip=<client_ip> ua=<user-agent>
Error line format:
  REQ-ERROR app=<app_name> sid=<session_id> rid=<request_id> user=<user_or_-> method=<METHOD> path=<PATH> ip=<client_ip> error=<repr(exception)>
"""


def init_logging(log_file=None, console_loglevel=logging.INFO, backup_count=300):
    """Initialize global logging once.

    If a TimedRotatingFileHandler is already present, we assume logging
    is configured and do nothing (prevents duplicate handlers on auto-reload).
    """
    root_logger = logging.getLogger()

    if any(isinstance(h, TimedRotatingFileHandler) for h in root_logger.handlers):
        return

    root_logger.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s"
    )

    class _ExcludeLoggersFilter(logging.Filter):
        def __init__(self, excluded):
            self._excluded = set(excluded)
        def filter(self, record):
            # Return False to drop record
            return record.name not in self._excluded

    excluded_logger_names = [
        'werkzeug',          # Flask dev server / built-in HTTP request logs
        'urllib3.connectionpool'  # (optional) very chatty HTTP client logs
    ]

    if log_file:
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8',
            utc=False
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(_ExcludeLoggersFilter(excluded_logger_names))
        root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_loglevel)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Reduce verbosity of werkzeug in console (still visible if >= WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    root_logger.debug(
        "Logging initialized. file='%s' rotation=daily backup_count=%d excluded=%s", log_file, backup_count, excluded_logger_names
    )


def _resolve_user_identifier():
    """Resolve a user identifier for logging (best-effort)."""
    return (
        session.get('email') or
        session.get('username') or
        session.get('id') or
        '-'  # sentinel
    )


def _ensure_session_id():
    """Create a stable session identifier if absent.

    Flask's signed cookie session has no intrinsic opaque id; we generate one
    and persist it under key 'sid'. Survives until session cleared.
    """
    sid = session.get('sid')
    if not sid:
        sid = uuid.uuid4().hex  # full 32 hex for uniqueness
        session['sid'] = sid
    return sid


def attach_request_logging(app, app_name='app', skip_static=True, skip_extensions=None,
                            skip_endpoints=None, skip_blueprints=None):
    """Attach per-request logging to a Flask app or Blueprint.

    Parameters:
        app: Flask application or Blueprint.
        app_name (str): Label in log lines.
        skip_static (bool): Skip Flask static endpoints.
        skip_extensions (Iterable[str]|None): Asset extensions to skip.
        skip_endpoints (Iterable[str]|None): Endpoint names to skip.
        skip_blueprints (Iterable[str]|None): Blueprint names to skip (to avoid double logging).
    """
    logger = logging.getLogger()

    if skip_extensions is None:
        skip_extensions = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.map')
    if skip_endpoints is None:
        skip_endpoints = set()
    else:
        skip_endpoints = set(skip_endpoints)
    if skip_blueprints is None:
        skip_blueprints = set()
    else:
        skip_blueprints = set(skip_blueprints)

    @app.before_request
    def _start_timer():
        g._req_start_time = time.time()
        g._req_id = uuid.uuid4().hex[:12]  # short request id
        g._session_id = _ensure_session_id()
        g._req_user = _resolve_user_identifier()

    @app.after_request
    def _log_request(response):
        try:
            endpoint = request.endpoint  # may be None
            path = request.path or ''
            bp = request.blueprint

            # Skip logic
            if bp in skip_blueprints:
                return response
            if skip_static and endpoint and ('static' == endpoint or endpoint.endswith('.static')):
                return response
            if any(path.endswith(ext) for ext in skip_extensions):
                return response
            if endpoint in skip_endpoints:
                return response

            start = getattr(g, '_req_start_time', time.time())
            duration_ms = (time.time() - start) * 1000.0
            rid = getattr(g, '_req_id', '-')
            sid = getattr(g, '_session_id', '-')
            user = getattr(g, '_req_user', '-')
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            ua = request.user_agent.string if request.user_agent else '-'

            logger.info(
                "REQ app=%s sid=%s rid=%s user=%s method=%s path=%s status=%s dur_ms=%.2f ip=%s ua=%s",
                app_name, sid, rid, user, request.method, path, response.status_code, duration_ms, ip, ua
            )
        except Exception as e:
            logger.warning("Failed to log request: %s", e)
        return response

    @app.teardown_request
    def _log_exception(exc):
        if exc is not None:
            rid = getattr(g, '_req_id', '-')
            sid = getattr(g, '_session_id', '-')
            user = getattr(g, '_req_user', '-')
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            logger.error(
                "REQ-ERROR app=%s sid=%s rid=%s user=%s method=%s path=%s ip=%s error=%s",
                app_name, sid, rid, user, request.method, request.path, ip, repr(exc)
            )
        return None

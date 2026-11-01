from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from werkzeug.serving import WSGIRequestHandler


def redact_reset_token_path(path):
    parts = urlsplit(path)
    if parts.path != "/reset-password" or not parts.query:
        return path
    query = parse_qsl(parts.query, keep_blank_values=True)
    if not any(key == "token" for key, _ in query):
        return path
    redacted_query = urlencode([
        (key, "[REDACTED]" if key == "token" else value)
        for key, value in query
    ])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, redacted_query, parts.fragment))


class RedactingWSGIRequestHandler(WSGIRequestHandler):
    def log_request(self, code="-", size="-"):
        original_path = getattr(self, "path", None)
        if original_path is not None:
            self.path = redact_reset_token_path(original_path)
        try:
            super().log_request(code, size)
        finally:
            if original_path is not None:
                self.path = original_path

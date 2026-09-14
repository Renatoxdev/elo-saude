import logging
import time
import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied, RequestDataTooBig, SuspiciousOperation
from django.http import Http404, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from .logging import request_context

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        context = {
            "request_id": uuid.uuid4().hex,
            "method": request.method
            if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
            else "OTHER",
            "route": "unmatched",
        }
        token = request_context.set(context)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = context["request_id"]
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed",
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                },
            )
            return response
        finally:
            request_context.reset(token)

    def process_view(self, request, view_func, view_args, view_kwargs):
        context = request_context.get()
        if context is not None:
            context["route"] = request.resolver_match.route


class APIErrorsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith("/api/v1/"):
            try:
                if len(request.body) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
                    return self.error_response(413)
            except RequestDataTooBig:
                return self.error_response(413)
        return None

    def process_exception(self, request, exception):
        if request.path.startswith("/api/"):
            if isinstance(exception, Http404):
                return self.error_response(404)
            if isinstance(exception, PermissionDenied):
                return self.error_response(403)
            if isinstance(exception, SuspiciousOperation):
                return self.error_response(400)
            logger.error(
                "api_error",
                exc_info=(type(exception), exception, exception.__traceback__),
                extra={"event": "api_error"},
            )
            return self.error_response(500)
        return None

    def process_response(self, request, response):
        if (
            request.path.startswith("/api/")
            and response.status_code >= 400
            and not response.get("Content-Type", "").startswith("application/json")
        ):
            return self.error_response(response.status_code)
        return response

    @staticmethod
    def error_response(status_code):
        codes = {
            400: "bad_request",
            403: "permission_denied",
            404: "not_found",
            413: "request_too_large",
        }
        return JsonResponse(
            {
                "error": {
                    "code": codes.get(status_code, "server_error"),
                    "details": "Requisição inválida." if status_code < 500 else "Erro interno.",
                }
            },
            status=status_code,
        )

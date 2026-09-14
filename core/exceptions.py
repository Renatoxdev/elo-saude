import logging

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class Conflict(APIException):
    status_code = 409
    default_detail = "A operação conflita com registros existentes."
    default_code = "conflict"


def api_exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        exc = Conflict("Exclua ou transfira as consultas antes de excluir o profissional.")
    elif isinstance(exc, IntegrityError):
        cause = exc.__cause__
        if getattr(getattr(cause, "diag", None), "constraint_name", None) == (
            "unique_professional_scheduled_at"
        ):
            exc = Conflict("Este profissional já tem uma consulta nesse instante.")
        elif getattr(cause, "sqlstate", None) == "23503":
            exc = Conflict("O vínculo com o profissional mudou. Consulte os registros novamente.")

    response = exception_handler(exc, context)
    if response is None:
        # Não registrar mensagem, payload ou variáveis da exceção: podem conter dados pessoais.
        logger.error(
            "api_error", exc_info=(type(exc), exc, exc.__traceback__), extra={"event": "api_error"}
        )
        return Response(
            {"error": {"code": "server_error", "details": "Erro interno do servidor."}}, status=500
        )
    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "error"),
            "details": response.data,
        }
    }
    return response

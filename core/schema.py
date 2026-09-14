from http import HTTPStatus


def document_errors(result, generator, request, public):
    """Aplica o contrato de erros compartilhado às operações de domínio."""
    result["components"]["schemas"]["APIError"] = {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "details"],
                "properties": {"code": {"type": "string"}, "details": {}},
            }
        },
    }
    for path, operations in result["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            codes = {400, 401, 406, 500}
            if "{" in path:
                codes.add(404)
            if method in {"post", "put", "patch"}:
                codes.update({413, 415})
            if "/auth/" in path or "/addresses/" in path:
                codes.add(429)
            if "/addresses/" in path:
                codes.add(503)
            if (
                "/appointments/" in path
                and method in {"post", "put", "patch"}
                or "/professionals/" in path
                and method == "delete"
            ):
                codes.add(409)
            for code in codes:
                operation["responses"][str(code)] = {
                    "description": HTTPStatus(code).phrase,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/APIError"},
                        }
                    },
                }
            for response in operation["responses"].values():
                response.setdefault("headers", {})["X-Request-ID"] = {
                    "description": "Identificador gerado pelo servidor para correlação dos logs.",
                    "schema": {"type": "string"},
                }
    return result

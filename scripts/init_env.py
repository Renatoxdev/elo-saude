"""Cria configuração local sem exibir secrets ou sobrescrever arquivos existentes."""

import os
import secrets
from pathlib import Path


def create_env(root: Path) -> bool:
    template = (root / ".env.example").read_text()
    for variable in ("DJANGO_SECRET_KEY", "DJANGO_JWT_SIGNING_KEY", "POSTGRES_PASSWORD"):
        template = template.replace(f"{variable}=\n", f"{variable}={secrets.token_urlsafe(64)}\n")
    try:
        descriptor = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w") as stream:
        stream.write(template)
    return True


if __name__ == "__main__":
    created = create_env(Path(__file__).resolve().parents[1])
    print(
        ".env criado; segredos não exibidos." if created else ".env já existe; arquivo preservado."
    )

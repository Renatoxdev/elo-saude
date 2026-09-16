"""Publica um commit validado no Render e aguarda sua disponibilização."""

import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DeployError(Exception):
    pass


def request_json(url, *, key=None, data=None):
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    try:
        with build_opener(NoRedirect).open(
            Request(url, data=body, headers=headers), timeout=30
        ) as response:
            return json.load(response)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        raise DeployError(f"HTTP {code}; consulte o painel do Render.") from None
    except (URLError, TimeoutError, ValueError):
        raise DeployError(
            "Falha de conexão ou resposta inválida; confira o deploy no Render."
        ) from None


def deploy(
    key,
    service_id,
    commit,
    repository,
    *,
    api_url="https://api.render.com/v1",
    timeout=900,
    interval=10,
):
    if not key or not re.fullmatch(r"srv-[a-z0-9]+", service_id):
        raise DeployError("Configure RENDER_API_KEY e RENDER_SERVICE_ID.")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise DeployError("O deploy exige o SHA completo do commit validado.")
    path = f"{api_url}/services/{service_id}"
    service = request_json(path, key=key)
    expected_repo = f"https://github.com/{repository}".lower().removesuffix(".git")
    actual_repo = service.get("repo", "").lower().removesuffix(".git")
    if actual_repo != expected_repo or service.get("branch") != "main":
        raise DeployError("O serviço deve apontar para este repositório e a branch main.")
    if service.get("autoDeploy") != "no":
        raise DeployError("Desative Auto-Deploy no Render para o GitHub controlar a publicação.")
    url = service.get("serviceDetails", {}).get("url", "")
    if not re.fullmatch(r"https://[a-z0-9-]+\.onrender\.com", url):
        raise DeployError("URL pública Render inválida.")
    # Não repetir POST automaticamente: uma falha de rede pode ocorrer após criar o deploy.
    created = request_json(path + "/deploys", key=key, data={"commitId": commit})
    deploy_id = created.get("id", "")
    if not re.fullmatch(r"dep-[a-z0-9]+", deploy_id):
        raise DeployError("Render não retornou um identificador de deploy válido.")
    print(f"Deploy iniciado: {deploy_id}", flush=True)
    wait_for_deploy(path + f"/deploys/{deploy_id}", key, commit, timeout=timeout, interval=interval)
    if request_json(url + "/health/ready/").get("status") != "ok":
        raise DeployError("Readiness não confirmou disponibilidade do banco.")
    return url


def wait_for_deploy(deploy_url, key, commit, *, timeout=900, interval=10):
    deadline = time.monotonic() + timeout
    pending = {
        "created",
        "queued",
        "build_in_progress",
        "update_in_progress",
        "pre_deploy_in_progress",
    }
    last_status = None
    while time.monotonic() < deadline:
        current = request_json(deploy_url, key=key)
        status = current.get("status")
        if status != last_status:
            print(f"Estado: {status}", flush=True)
            last_status = status
        if status == "live":
            if current.get("commit", {}).get("id") != commit:
                raise DeployError("O commit publicado difere do commit validado.")
            return
        if status not in pending:
            raise DeployError("Deploy não ficou ativo; consulte os logs do Render.")
        time.sleep(interval)
    raise DeployError("Prazo de deploy excedido; confira a execução remota antes de repetir.")


def main():
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise DeployError("Deploy permitido somente a partir de main.")
    if os.environ.get("DEPLOY_ENVIRONMENT") not in {"staging", "production"}:
        raise DeployError("Ambiente de deploy inválido.")
    url = deploy(
        os.environ.get("RENDER_API_KEY", ""),
        os.environ.get("RENDER_SERVICE_ID", ""),
        os.environ.get("GITHUB_SHA", ""),
        os.environ.get("GITHUB_REPOSITORY", ""),
    )
    print(f"Commit validado disponível em {url}")


if __name__ == "__main__":
    try:
        main()
    except DeployError as exc:
        raise SystemExit(str(exc)) from None

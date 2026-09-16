# Revisão complementar — 16/09/2026

## Alterações realizadas

- `README.md`: links e estado real do ensaio, operação e proposta Asaas.
- `architecture/RENDER.md`: referência ao ensaio e decisão sobre digest.
- `architecture/OPERATIONS.md`: runbook, critérios de validação, monitoração,
  alertas, backup/restore, cache e throttling distribuídos.
- `architecture/ROLLBACK_STAGING.md` e JSON em `architecture/evidence/`: evidência
  do rollback e retorno, com dados de controle e status, sem credenciais.
- `architecture/ASAAS.md`: proposta de extensão financeira sem implementação.

Nenhum código de domínio, migration, Dockerfile, workflow ou configuração
permanente de serviço foi alterado. As mudanças previamente staged pelo autor
em skills e `architecture/AWS.md` foram preservadas fora destes commits.

## Rollback executado

Staging: `e1fc9bb` → `bd5f91e` → `e1fc9bb`. Foram 45 verificações HTTPS aprovadas,
15 em cada fase. Usuário, dados temporários e tokens removidos; automação GitHub
restaurada ao valor original. Produção permaneceu no mesmo deploy e não recebeu
testes. [SHAs completos, IDs e horários](ROLLBACK_STAGING.md).

## CI/CD e Docker

Antes e depois: testes/build GitHub; Render faz builds independentes por serviço,
com mesmo SHA na promoção. Não houve migração silenciosa de infraestrutura.
Digest único foi avaliado e documentado como evolução image-backed + GHCR. O
[runbook](OPERATIONS.md#imagem-única-decisão-e-migração-proposta) explica obtenção do
digest do manifesto, passagem entre jobs sem rebuild e retenção para rollback.
Não há evidência de promoção de digest nos serviços atuais.

## Operação e escalabilidade

Monitoramento, alertas com severidade, backup diário criptografado/externo,
retenção e restore isolado foram documentados como propostas. RPO/RTO são metas,
não resultados medidos. Nenhum restore de PostgreSQL foi executado.

Cache ViaCEP e throttling são locais ao processo. A proposta Redis distingue
estado compartilhado de atomicidade; quota concorrente estrita exige algoritmo
atômico/gateway, além de validação da identidade atrás do proxy. Redis não foi
instalado apenas para cumprir checklist.

## Asaas

Proposta de adapter, reconciliação, persistência e webhook idempotente; sem mock
executável nem chamada financeira. [Detalhes](ASAAS.md).

## Verificações locais após as alterações

`make quality`: 8 testes auxiliares e 71 testes Django aprovados; cobertura
combinada de linhas/ramificações **97,20%**, preservada. Ruff lint e format,
consistência do lock, Django checks, migrations e OpenAPI com
`--validate --fail-on-warn` aprovados. Relatórios locais: `coverage.xml`,
`htmlcov/index.html` e `artifacts/openapi.yaml` (gerados, não versionados).

Docker build local aprovado; imagem executada para verificar imports Django/
Gunicorn, UID 10001, manifest de estáticos e ausência de `.env`/`.env.render`.
Não se confunde essa imagem local com os artefatos usados no Render.

Não há type checker configurado no projeto; nenhum resultado mypy/pyright é
alegado. Código da aplicação não foi modificado nesta revisão. A suíte existente
cobre conflitos, autenticação, erros, contrato OpenAPI e health checks.

Varredura do histórico Git por valores secretos locais conhecidos e assinaturas
de credenciais: 89 blobs examinados, nenhum achado. `.env.render` continua
ignorado; somente `.env.example` é rastreado. Revisão do diff sem secrets ou
alterações funcionais. Essa verificação tem escopo limitado e não equivale a
prova de ausência de qualquer segredo possível.

## Pendências e escolhas explícitas

Nenhuma ação manual ficou pendente para o ensaio de rollback. Migração para
imagem única, provisionamento de monitoramento/alertas/backup, teste de restore,
Redis e integração Asaas permanecem evoluções futuras deliberadas. Dependem de
configuração, orçamento e validação próprios; não são descritos como executados.

## Evidências para a equipe avaliadora

> Realizado ensaio controlado exclusivamente em staging em 16/09/2026:
> e1fc9bb → bd5f91e → e1fc9bb, com 45 verificações HTTPS aprovadas, incluindo
> readiness, JWT e fluxo de profissionais/consultas. Evidências de deploy, SHAs,
> horários e limpeza estão em architecture/ROLLBACK_STAGING.md. Produção foi
> preservada. Suíte local: 71 testes Django + 8 auxiliares; cobertura 97,20%;
> OpenAPI, lint e Docker aprovados. O runbook registra operação, backup/restore,
> cache/throttling distribuídos e análise de promoção por digest. Esta última
> permanece proposta: o Render atual continua implantando por commit.

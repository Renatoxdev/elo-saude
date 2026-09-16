# Elo Saúde

API REST de profissionais da saúde e consultas, desenvolvida como desafio técnico
para a Lacrei Saúde. Possui CRUD, autenticação JWT, consulta ViaCEP, OpenAPI e
ambiente Docker com PostgreSQL.

**Implementado e validado:** domínio, API, segurança da aplicação, logs estruturados,
Docker, verificações de qualidade e CI no GitHub (lint, testes PostgreSQL e build).
**Staging publicado no Render:** fluxo autenticado validado por HTTPS.
**Render:** configuração de produção e automação em validação.
Veja o [guia de implantação, CI/CD e rollback no Render](architecture/RENDER.md).
A arquitetura AWS permanece como proposta.

## Staging para avaliação

- [Swagger](https://elo-saude-staging.onrender.com/api/docs/)
- [Readiness](https://elo-saude-staging.onrender.com/health/ready/)

Em 15/09/2026, foram verificados por HTTPS: readiness com resposta 200 e
`{"status":"ok"}`, Swagger com resposta 200 e listagem de profissionais sem token
com resposta 401. Também passaram 21 verificações HTTP no staging: login JWT,
criação/leitura/atualização/exclusão de profissionais e consultas, filtro por
profissional, payload inválido, conflito de agenda, exclusão protegida e rejeição
de refresh revogado. O banco remoto usa PostgreSQL 18.6; CI usa PostgreSQL 17.
Usuário, registros e tokens temporários foram removidos ao final. Essas verificações
complementam a suíte automatizada; não são teste de carga. Não há credenciais públicas.
O plano gratuito pode suspender o serviço por inatividade e atrasar o primeiro acesso.

## Início rápido com Docker

Pré-requisitos: Python 3 para gerar a configuração local, Docker Engine, Compose e
Buildx. Execute os comandos na raiz do repositório:

```bash
python3 scripts/init_env.py
docker compose config --quiet
docker compose up --build -d --wait
```

O script cria `.env` com três secrets aleatórios distintos, sem exibi-los, com
permissões `0600`. Se o arquivo já existir, preserva seu conteúdo. As credenciais
padrão de desenvolvimento identificam o banco, mas não há senha fixa.

Acesse [Swagger](http://127.0.0.1:8000/api/docs/),
[ReDoc](http://127.0.0.1:8000/api/redoc/) ou o
[schema JSON](http://127.0.0.1:8000/api/schema/).
Para provisionar seu usuário administrativo:

```bash
docker compose exec api python manage.py createsuperuser
```

O [admin](http://127.0.0.1:8000/admin/) permite criar outros usuários ativos.
Não há cadastro público, credencial padrão ou usuário demonstrativo persistente.

## Stack e arquitetura

- Python 3.12–3.14, Django 5.2 LTS e Django REST Framework.
- PostgreSQL 17 com Psycopg 3; nenhum fallback para SQLite.
- Poetry com lockfile e grupos de runtime/desenvolvimento.
- Simple JWT, django-filter, django-environ e django-cors-headers.
- HTTPX e phonenumbers para consulta HTTP e validação de telefone.
- drf-spectacular/sidecar, Gunicorn e WhiteNoise.
- Ruff, coverage e openapi-schema-validator para qualidade.

As versões resolvidas estão em `poetry.lock`. O ambiente local foi validado com
Python 3.14.7, Poetry 2.4.3 e PostgreSQL 17.11; Python 3.12 e 3.13 ainda não foram
executados nesta avaliação. Docker foi validado em Linux com daemon rootless.

```text
config/         # settings por ambiente, URLs, WSGI e ASGI
professionals/  # cadastro, contatos, endereço e testes
appointments/   # consultas, filtros, integridade e testes
addresses/      # cliente ViaCEP e consulta auxiliar
core/           # autenticação, erros, logs, healthchecks e testes
scripts/        # preparação local sem sobrescrever secrets
Makefile        # comandos de qualidade
```

Fluxo: URL → ViewSet → Serializer → ORM → PostgreSQL. Os serializers validam e
normalizam a entrada. Chave estrangeira e unicidade de agenda também existem no
banco. Operações com risco de conflito usam transações. A consulta ViaCEP é
separada das gravações e não impede cadastro manual durante falhas externas.

## Desenvolvimento sem containers

Pré-requisitos adicionais: Poetry >=2.2,<3, GNU Make para os atalhos e PostgreSQL
acessível, com banco/usuário provisionados. O usuário de testes precisa de
`CREATEDB`; esse privilégio não é apropriado ao usuário da aplicação em produção.

Instale Poetry conforme a [documentação oficial](https://python-poetry.org/docs/#installation).
Se estiver em `~/.local/bin`, inclua esse diretório no PATH.

```bash
poetry install
python3 scripts/init_env.py
```

Ajuste `POSTGRES_*` no `.env` para seu banco. O script gera uma senha para um banco
novo: em um banco existente, informe as credenciais correspondentes.

```bash
poetry run python manage.py wait_for_db
poetry run python manage.py migrate --noinput
poetry run python manage.py collectstatic --noinput
poetry run python manage.py createsuperuser
poetry run python manage.py runserver 127.0.0.1:8000 --noreload
```

Use `runserver` somente no desenvolvimento. O servidor da imagem é Gunicorn.
O PostgreSQL do Compose e um PostgreSQL instalado no host são instâncias separadas.

## Autenticação e permissões

Envie JSON para `POST /api/v1/auth/token/`:

```json
{"username": "seu_usuario", "password": "sua_senha"}
```

A resposta contém `access` e `refresh`. Nas chamadas de domínio, envie
`Authorization: Bearer <access>`. O access dura 5 minutos e o refresh, 1 dia.

| Operação | Endpoint | Corpo JSON |
|---|---|---|
| Login | `POST /api/v1/auth/token/` | `username` e `password` |
| Renovar | `POST /api/v1/auth/token/refresh/` | `{"refresh": "<refresh>"}` |
| Revogar | `POST /api/v1/auth/token/revoke/` | `{"refresh": "<refresh>"}` |

A renovação emite um novo par e coloca o refresh anterior na blacklist. Revogação
retorna `200 {}` e impede o uso posterior do refresh. Um access já emitido continua
válido até expirar; desativar o usuário impede seu acesso ao domínio.

Os três endpoints de autenticação verificam a credencial apresentada, sem exigir
access prévio. Todos os usuários ativos provisionados compartilham acesso aos
registros. O admin usa sessão com CSRF; a API usa JWT.

## Endpoints e exemplos

Use a barra final: URLs sem ela retornam `404`, evitando redirecionar escritas.
Todos os endpoints abaixo exigem JWT:

| Métodos | URL | Operação |
|---|---|---|
| GET, POST | `/api/v1/professionals/` | Listar/criar profissionais |
| GET, PUT, PATCH, DELETE | `/api/v1/professionals/{id}/` | Detalhar/atualizar/excluir |
| GET, POST | `/api/v1/appointments/` | Listar/criar consultas |
| GET, PUT, PATCH, DELETE | `/api/v1/appointments/{id}/` | Detalhar/atualizar/excluir |
| GET | `/api/v1/appointments/?professional_id=123` | Filtrar consultas |
| GET | `/api/v1/addresses/01001000/` | Consultar endereço por CEP |

Listagens têm 20 itens por página, ordenação determinística e formato
`count`, `next`, `previous`, `results`. Use `?page=2`. Filtro com ID inválido retorna
`400`; ID válido sem consultas retorna lista vazia.

### Profissional

```json
{
  "social_name": "Alex",
  "profession": "Psicologia",
  "contact_email": "alex@example.test",
  "contact_phone": "(11) 91234-5678",
  "postal_code": "01001-000",
  "street": "Praça da Sé",
  "number": "s/n",
  "complement": "",
  "neighborhood": "Sé",
  "city": "São Paulo",
  "state": "SP"
}
```

Todos os campos acima são obrigatórios, exceto `complement`. Telefone fixo ou móvel
brasileiro com DDD é normalizado para E.164. CEP aceita hífen e é salvo somente
com dígitos. UF deve ser uma sigla brasileira em maiúsculas. Número aceita texto,
como `s/n` ou `123A`.

Nome social e profissão preservam acentos/apóstrofos, removendo somente espaços
nas extremidades. Não exigimos sobrenome. Contatos não são únicos, permitindo
compartilhamento por clínicas. Validação de formato não comprova titularidade.

### Consulta

```json
{"professional": 123, "scheduled_at": "2020-01-02T09:00:00-03:00"}
```

Substitua `123` pelo ID retornado no cadastro. Exigimos data e horário ISO 8601
com fuso explícito. Consultas passadas são aceitas para histórico.

O mesmo profissional não pode ter consultas no mesmo instante, inclusive quando
as entradas usam fusos diferentes. Conflitos retornam `409`. Sem duração ou
horário final, essa regra não detecta sobreposição de intervalos.

Excluir profissional com consultas retorna `409`: antes, exclua ou transfira suas
consultas. Excluir uma consulta preserva o profissional. `id`, `created_at` e
`updated_at` são campos gerados pelo servidor e somente leitura.

## Contrato e documentação OpenAPI

A API recebe e retorna JSON. Criação usa `201`, leitura/atualização `200`, exclusão
`204` sem corpo. Erros têm envelope uniforme:

```json
{"error": {"code": "invalid", "details": {"contact_email": ["Este campo é obrigatório."]}}}
```

`details` pode conter erros por campo ou mensagem geral. Os status incluem `400`
(dados inválidos), `401` (autenticação), `404` (ausência), `409` (conflito), `413`
(corpo excessivo), `415` (tipo não suportado), `429` (limite) e `503` (ViaCEP indisponível).
Erros inesperados recebem mensagens genéricas, sem detalhes internos.

Swagger e ReDoc são páginas HTML públicas; não concedem acesso aos registros.
Faça login pelo endpoint de token e use **Authorize** no Swagger. A autorização
não é persistida pela interface. JS/CSS são locais, via sidecar/WhiteNoise, sem CDN.

O schema contém exemplos executados nos testes, paginação, JWT e respostas de
conflito. O teste de contrato usa OpenAPI 3.0, incluindo campos que aceitam `null`.

## ViaCEP

A consulta ao [ViaCEP](https://viacep.com.br/) é auxiliar e retorna `postal_code`,
`street`, `complement`, `neighborhood`, `city` e `state`. Número e complemento
específico da unidade continuam sob responsabilidade de quem cadastra.
CEPs genéricos podem retornar logradouro/bairro vazios, a preencher manualmente.

- CEP malformado: `400`, sem chamada externa; inexistente: `404`.
- Timeout, resposta inválida ou falha HTTP: `503`.
- Conexão limitada a 2 segundos e espera de leitura a 3 segundos por operação.
- Resposta limitada a 32 KiB; sem redirects ou retries automáticos.
- Cache de resultados válidos por uma hora; falhas não ficam em cache.

O CRUD não consulta ViaCEP. A consulta não comprova local de atendimento.

## Settings e variáveis de ambiente

`local.py` lê `.env` sem sobrescrever o ambiente do processo. Staging/produção
recebem variáveis externas e compartilham políticas em `deployment.py`.
`manage.py` usa local por padrão; WSGI/ASGI usam produção por padrão.

| Variável | Uso |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.local`, `.staging` ou `.production`, antes de iniciar. |
| `DJANGO_SECRET_KEY` | Chave Django obrigatória, forte em staging/produção. |
| `DJANGO_JWT_SIGNING_KEY` | Chave JWT forte, obrigatória e diferente da chave Django. |
| `DJANGO_DEBUG` | `true` é rejeitado em staging/produção. |
| `DJANGO_ALLOWED_HOSTS` | Hosts separados por vírgula; explícitos e sem curingas em staging/produção. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Origens CORS separadas por vírgula; nenhuma por padrão. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origens confiáveis para CSRF do admin. |
| `DJANGO_LOG_LEVEL` | Nível do logger raiz; padrão `INFO`. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Banco e credenciais obrigatórias. |
| `POSTGRES_HOST`, `POSTGRES_PORT` | Host obrigatório; porta padrão `5432`. |
| `POSTGRES_CONNECT_TIMEOUT` | Timeout de conexão, padrão 5 segundos. |
| `POSTGRES_SSLMODE` | Staging/produção exigem `require`, `verify-ca` ou `verify-full`. |
| `POSTGRES_SSLROOTCERT` | CA para verificação do certificado do banco. |
| `DJANGO_TRUST_PROXY_SSL_HEADER` | Confiança explícita em `X-Forwarded-Proto`; padrão `false`. |
| `WEB_CONCURRENCY` | Quantidade de workers Gunicorn; padrão 2. |

Variáveis PostgreSQL exportadas têm a mesma precedência em `db`, `migrate` e `api`.
Em volumes já inicializados, alterar `.env` não troca credenciais no PostgreSQL:
a alteração deve ser feita também no banco, preservando seus dados.

## Segurança e logging

- ORM sem SQL concatenado com entrada do usuário. Probes usam apenas `SELECT 1`.
- Validação e normalização explícitas, sem sanitização destrutiva.
- Django não chama `full_clean()` em `save()` direto: escritas fora dos serializers
  ou formulários precisam validar o model. FK e unicidade também são restrições SQL.
- HTTPS, cookies seguros e hosts explícitos em ambientes publicados.
- CORS restritivo; ele não substitui autenticação.
- Corpos sob `/api/v1/` limitados a 64 KiB.
- Sem paciente, diagnóstico, CPF ou dados de pagamento no domínio atual.

Logs da aplicação e Gunicorn são JSON com campos permitidos: horário UTC, nível,
logger, evento e contexto de requisição (ID gerado pelo servidor, método e padrão
da rota). Acesso inclui status e duração. `X-Request-ID` permite correlação.

Não serializamos corpos, cookies, cabeçalhos, query strings, parâmetros concretos
de URL ou mensagens arbitrárias de bibliotecas. Exceções incluem tipo e até oito
frames com arquivo/função/linha, sem mensagem, código-fonte ou variáveis locais.
Testes inserem deliberadamente valores sensíveis para conferir sua ausência nos logs.
Logs de PostgreSQL/infraestrutura exigirão configuração e retenção próprias na AWS.

Autenticação tem limite de 10/minuto por IP; CEP, 30/minuto por usuário. Cache e
throttling são por processo. Não constituem proteção distribuída contra força
bruta. Não confiamos em `X-Forwarded-For` do cliente; atrás de um proxy, vários
clientes podem compartilhar o mesmo limite até configurarmos a topologia.

O check de deploy mantém `security.W005` e `security.W021` visíveis: HSTS para
subdomínios/preload permanecem desativados até validar domínio e HTTPS. HSTS inicia
em uma hora. Proxy, limites de rede, certificados e RDS ainda não foram validados.

## Qualidade e testes

Com dependências instaladas, `.env` válido, PostgreSQL disponível e migrations aplicadas:

```bash
make quality
```

Resultado em 12/09/2026: **71 testes aprovados e 97,20% de cobertura combinada de
linhas e ramificações**, no escopo descrito abaixo. Esse comando falha se alguma
etapa falhar. Há também três testes de regressão dos workflows, fora do percentual
de cobertura da aplicação. Atalhos individuais:

| Comando | Verificação/artefato |
|---|---|
| `make check` | Lockfile, Ruff, regressões dos workflows, Django e migrations pendentes. |
| `make schema` | Schema validado sem avisos em `artifacts/openapi.yaml`. |
| `make test` | Coleta de estáticos, testes, cobertura de linhas/ramificações, HTML e XML. |

Se Poetry não estiver no PATH, use `make quality POETRY=/caminho/para/poetry`.
Para executar apenas a suíte: `poetry run python manage.py test`. Em um checkout
novo, executar antes `poetry run python manage.py collectstatic --noinput`;
`make test` já prepara os estáticos necessários para testar Swagger/ReDoc.
Os comandos completos de cada etapa estão no Makefile.

O relatório HTML fica em `htmlcov/index.html`; o XML, em `coverage.xml`.
Cobertura inclui subprocessos dos testes de settings. Testes, migrations geradas
e os arquivos de entrada WSGI/ASGI ficam fora do percentual; os settings permanecem
incluídos. A cobertura não substitui os cenários de comportamento.

A suíte verifica CRUD, JWT real, filtro, paginação, validações, erros JSON, CORS,
logs, contrato OpenAPI, restrições PostgreSQL e concorrência. O tratamento de erros
de integridade também é testado com violações reais do banco, de forma determinística.
As falhas de ViaCEP usam HTTP real contra servidor local controlado; a suíte não
exige internet. Uma consulta HTTPS ao serviço real também foi validada separadamente.

Os testes não usam SQLite. A imagem de runtime não instala dependências de teste;
execute qualidade no ambiente Poetry com PostgreSQL de desenvolvimento/testes.

## Operação dos containers

O Compose inicia `db` saudável, depois `migrate`, e somente após seu sucesso inicia
`api`. A API escuta apenas em `127.0.0.1:8000`; a porta do banco não é publicada.
O banco usa volume nomeado. Os defaults administrativos da imagem PostgreSQL são
exclusivos do desenvolvimento; produção exige papéis com permissões mínimas.

A imagem usa Python slim, Poetry apenas no builder e runtime com UID 10001.
No Compose, a API tem filesystem somente leitura, `/tmp` temporário, capabilities
removidas e novos privilégios bloqueados. `.env`, `.git`, notas e caches não entram
na imagem. Estáticos são coletados no build sem banco ou secrets de runtime.

```bash
docker compose ps -a
docker compose run --rm migrate
docker compose exec api python manage.py migrate --check
docker compose logs --tail=50 api
docker compose stop
```

`stop` preserva o volume. Migrations são tarefa separada, nunca executadas por cada
worker. `wait_for_db` espera por padrão 30 segundos, com prazo verificado entre
conexões; cada conexão respeita `POSTGRES_CONNECT_TIMEOUT`. Valores não positivos,
NaN e infinitos são rejeitados.

Não compartilhe `docker compose config` expandido: ele pode mostrar secrets.
Use `config --quiet` para validar. O Compose sobrescreve settings para local com
`DEBUG=false`, HTTP e banco sem TLS na rede interna. Não é um deploy de produção.

## Healthchecks e validação operacional

`/health/live/` verifica o processo; `/health/ready/` consulta o PostgreSQL e retorna
200 ou 503 com estado genérico. Ambos aceitam GET/HEAD anonimamente e não retornam
detalhes internos. O healthcheck da imagem usa readiness.

Os probes são isentos do redirect HTTPS. O probe interno usa o primeiro host de
`DJANGO_ALLOWED_HOSTS`; os demais caminhos seguem a política HTTPS configurada.

Foram executados: build, Compose, estáticos, JWT/CRUD via HTTP no container,
execução sem root, isolamento de arquivos e recuperação após parar/reiniciar o
banco. Em projeto isolado, falha de migrations bloqueou a API e um registro
sobreviveu à recriação do container do banco. Dados de teste foram removidos.

## Decisões técnicas e próximos passos

O ambiente de avaliação usa **Render + Neon**, com procedimento de setup,
variáveis, promoção e rollback no [guia Render](architecture/RENDER.md).
A configuração ECS/AWS abaixo é alternativa e permanece desativada.

| Decisão | Justificativa |
|---|---|
| Monólito Django | Arquitetura pequena e explicável, sem abstrações prematuras. |
| E-mail e telefone | Dois canais de contato, com validação de formato. |
| Endereço separado | Validação por campo e auxílio por CEP. |
| Profissão livre | O enunciado não fornece catálogo. |
| Horário com fuso e histórico | Comparar instantes corretamente e registrar consultas passadas. |
| Exclusão protegida | Evitar eliminação automática do histórico vinculado. |
| ViaCEP separado do cadastro | Permitir operação manual quando o provedor falha. |
| JWT com rotação | Acesso curto e revogação do refresh, sem cadastro público. |

**CI validado no GitHub; deploy AWS não executado:**
[Pipeline](.github/workflows/pipeline.yml) executa lint → testes PostgreSQL 17 →
build Docker. PRs não recebem credenciais AWS. Relatórios de cobertura/OpenAPI
ficam disponíveis por sete dias; a imagem do build, por três dias.

O [deploy reutilizável](.github/workflows/deploy.yml) usa OIDC, publica o build no
ECR e referencia a imagem por digest. Executa migrations em uma tarefa Fargate,
confere seu sucesso e só então atualiza o serviço. Aguarda estabilidade e confirma
que a revisão esperada está ativa, para não confundir rollback automático com sucesso.

Para habilitar deploy, primeiro provisionar AWS e configurar GitHub Environments
`staging` e `production`. Em cada ambiente, definir estas **Variables**:

| Variável | Valor esperado |
|---|---|
| `AWS_REGION` | Região do ambiente. |
| `AWS_ROLE_ARN` | Role de deploy assumida via OIDC, restrita ao repositório e Environment. |
| `ECR_REPOSITORY` | Nome do repositório ECR, com tags imutáveis. |
| `ECS_CLUSTER` / `ECS_SERVICE` | Cluster e serviço ECS existentes. |
| `ECS_TASK_DEFINITION` | ARN completo com revisão de uma task definition base do ambiente. |
| `ECS_SUBNETS` / `ECS_SECURITY_GROUPS` | IDs separados por vírgulas; subnets privadas com acesso aos serviços AWS. |

A task definition precisa de um container essencial chamado `api`, arquitetura
Linux/x86_64, logs CloudWatch, settings do ambiente, conexão RDS com TLS e secrets
referenciados pelo Secrets Manager. O serviço deve usar controller `ECS`, healthcheck
no ALB e deployment circuit breaker com rollback. O banco deve aceitar a conexão
da tarefa de migration; ela usa a mesma configuração de rede e secrets da API.
A task definition base deve ser atualizada explicitamente quando a configuração
mudar; o workflow altera apenas a imagem. Não colocar valores de secrets nas Variables.

Staging e produção promovem o mesmo digest do ECR: o execution role de produção
precisa conseguir ler o repositório usado em staging, inclusive em contas distintas.
A role de CI precisa de permissões limitadas para ECR, leitura/registro de task
definitions, RunTask/DescribeTasks, DescribeServices/UpdateService e PassRole apenas
para as roles ECS necessárias. A política exata será definida com a infraestrutura.

Proteger `production` com aprovação obrigatória, impedir autoaprovação e restringir
ambos os ambientes à branch `main`. Configurar a confiança OIDC para o Environment
correspondente e exigir lint/tests/build na proteção da branch. Essas proteções são
configurações do GitHub e **não são criadas pelo YAML**.

Depois disso, definir a Variable do **repositório** `AWS_DEPLOY_ENABLED=true`.
Enquanto ausente, CI roda e deploy é ignorado. Push em `main` publica em staging.
Para produção, executar manualmente `Pipeline` na branch `main` com `production`
marcado: a execução repete as validações, publica em staging e promove esse mesmo
digest após a aprovação de produção. Não promove imagens arbitrárias nem refaz o
build entre ambientes. Produção rejeita digest ausente ou malformado antes de
obter credenciais AWS; não há fallback para publicação de uma nova imagem.
Deploys não são cancelados automaticamente durante migrations. Um cancelamento
manual ou timeout do job não garante que a tarefa ECS pare: antes de repetir um
deploy, verificar a tarefa de migration no ECS e aguardar seu término.

Validação local: sintaxe dos workflows com actionlint, comandos de qualidade em
cópia limpa sem `.env` ou estáticos pré-gerados (configuração via ambiente),
regressões de promoção/shell e build Docker. Em 14/09/2026, a [execução 34841429543](https://github.com/Renatoxdev/elo-saude/actions/runs/34841429543)
concluiu lint, testes PostgreSQL e build Docker com sucesso no GitHub. Staging e
production foram ignorados porque o deploy AWS está desativado. OIDC, migrations
no ECS e rollout AWS continuam não executados; exigem infraestrutura configurada.
Referências: [PostgreSQL em Actions](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)
e [ação oficial de deploy ECS](https://github.com/aws-actions/amazon-ecs-deploy-task-definition).

**Limitação da entrega:** não foi possível ativar uma conta AWS. Os ambientes
staging e production não foram publicados na AWS; OIDC e deploy ECS não foram
validados. Staging foi publicado no Render, conforme a seção de avaliação acima.
A [arquitetura AWS e o roteiro de implantação/rollback](architecture/AWS.md)
descrevem os componentes, o isolamento e as verificações pendentes. Trata-se de
um projeto de arquitetura, sem provisionamento ou templates de infraestrutura.

**AWS proposta, sem recursos criados:** ECR, ECS/Fargate, ALB com HTTPS, RDS privado,
CloudWatch e Secrets Manager, separados por ambiente. Região, orçamento, domínio,
credenciais e configuração de rede ainda precisam ser definidos.

**Rollback proposto, não executado:** retornar à revisão/imagem anterior do serviço.
Migrations devem manter compatibilidade durante a transição. Voltar a aplicação
não desfaz o banco; restauração e correções de dados exigem procedimentos próprios.

**Asaas futura, não implementada:** módulo de pagamentos separado do domínio,
com criação de cobrança/split, cliente com timeouts, registro de eventos de webhook
e processamento idempotente. Autenticação do webhook, retries e reconciliação de
cobranças após timeout serão definidos com a documentação oficial na etapa da integração.
Nenhuma cobrança real ou mock de pagamento foi criado.

Ainda faltam implantação real, políticas de proxy/cache compartilhado, monitoramento,
backup/restauração e auditoria final. Não considerar a solução pronta para produção.


## Problemas encontrados e resolvidos

| Problema | Causa e correção |
|---|---|
| Banco e API com credenciais diferentes | Interpolação do Compose e env_file tinham precedência diferente; os três serviços agora recebem os mesmos campos explicitamente. |
| Espera por banco sem prazo efetivo | NaN e infinito eram aceitos; agora são rejeitados antes de conectar. |
| CI falhava em checkout novo | Swagger precisava do manifest de estáticos; `make test` agora executa collectstatic antes da suíte. |
| Produção aceitava digest vazio | O workflow agora rejeita a promoção antes de obter credenciais, sem publicar outra imagem. |
| Exportação da imagem podia mascarar falha | Bash explícito habilita pipefail nos workflows; falha no produtor interrompe o job mesmo com gzip bem-sucedido. |
| Validação incorreta de campos nulos do schema | Um validador JSON Schema não reconhecia nullable do OpenAPI 3.0; substituído por OAS30Validator, mantendo o contrato. |

Os testes de regressão e as verificações operacionais estão descritos acima.

# Operação da Elo Saúde

Este runbook complementa o [guia Render](RENDER.md). Distingue a configuração
existente de propostas ainda não provisionadas. Evidências datadas estão em
[ensaio de staging](ROLLBACK_STAGING.md). Não contém credenciais.

## Deploy e verificação

Hoje, `Pipeline` executa lint, testes e build no GitHub. Em `main`, publica o SHA
em staging; produção depende de execução manual com `production=true`, após
staging saudável. Render reconstrói o Dockerfile em cada serviço. Os serviços
usam bancos e chaves distintos. Auto-Deploy do Render permanece desligado.

Antes de publicar: revisar diff/migrations, obter CI verde, confirmar ambiente e
registrar SHA, execução CI e ID de deploy. Não fazer migrations concorrentes.
O script de início executa `migrate`; alterações devem ser compatíveis com a
versão anterior enquanto ela ainda atende tráfego. Preferir expandir o schema,
migrar dados e só remover campos em uma versão posterior.

Após deploy, registrar horário UTC, SHA confirmado pela API do Render e estado
`live`. Não deduzir o SHA apenas da resposta HTTP da aplicação.

```sh
curl --fail --max-time 120 https://elo-saude-staging.onrender.com/health/live/
curl --fail --max-time 120 https://elo-saude-staging.onrender.com/health/ready/
curl --fail --max-time 120 -o /dev/null https://elo-saude-staging.onrender.com/api/docs/
curl --max-time 120 -o /dev/null -w '%{http_code}\n' \
  https://elo-saude-staging.onrender.com/api/v1/professionals/
```

Esperado: liveness e readiness `200 {"status":"ok"}`, Swagger `200`, domínio sem
token `401`. Readiness consulta PostgreSQL (`SELECT 1`); liveness não depende dele.
Em staging, provisionar usuário temporário sem privilégios administrativos,
usar `/api/v1/auth/token/` e verificar criação/leitura/alteração de profissional,
criação de consulta, filtro `professional_id`, proteção de exclusão `409` e
exclusão dos próprios registros de teste. Revogar refresh e remover usuário e
registros de tokens. Nunca imprimir JWT, senha ou payloads pessoais nos logs.
Não executar `manage.py test` contra banco publicado.

Health checks não provam o CRUD. Uma falha de readiness deve bloquear a promoção;
uma falha funcional exige investigação mesmo com health verde. Para free/cold
start, distinguir o tempo de despertar de latência com aplicação aquecida.

## Rollback controlado: apenas staging no ensaio

1. Registrar deploy atualmente `live` e um deploy anterior bem-sucedido com
   artefato retido. Conferir diferença de código, migrations e mudanças de secrets
   desde aquela versão. Se o build foi removido, não chamar rebuild de rollback
   do mesmo artefato: registrar explicitamente essa diferença.
2. Salvar o valor de `RENDER_DEPLOY_ENABLED`, definir `false` e confirmar que não
   há workflows/deploys em andamento ou na fila. Essa variável não cancela jobs
   que já foram iniciados. Manter Auto-Deploy do Render desligado.
3. Validar o estado inicial com o smoke acima. Não prosseguir se ele falhar.
4. Em **elo-saude-staging → Deploys**, selecionar o deploy anterior e **Rollback**.
   Alternativa API: `POST /v1/services/{stagingServiceId}/rollback` com JSON
   `{"deployId":"ID_DO_DEPLOY_ANTERIOR"}` e Bearer token somente no header. Não
   enviar token em URL nem colocar a chave no histórico do terminal.
5. Guardar ID retornado e consultar `GET /v1/services/{stagingServiceId}/deploys/{id}`
   até `live`, com prazo limitado (15 minutos). Conferir SHA exato. Timeout não
   significa que a operação remota parou: consultar o estado antes de repetir.
6. Repetir health e smoke autenticado, guardar status/timestamps e limpar somente
   dados temporários identificados pelo ensaio.
7. Mesmo em falha do smoke, retornar ao deploy inicial pelo mesmo procedimento;
   validar SHA, health e fluxo autenticado novamente. Se o retorno falhar, manter
   automação pausada e investigar. Não promover produção.
8. Após retorno confirmado, restaurar o valor original da variável GitHub e
   registrar a limpeza dos dados e o estado final.

O rollback recupera artefato e certas configurações do deploy anterior, inclusive
variáveis de ambiente. Verificar previamente credenciais rotacionadas e comando
de início. Ele **não restaura PostgreSQL**. Não reverter migrations automaticamente.
A retenção de builds limita quais versões podem ser restauradas.
[Comportamento do Render](https://render.com/docs/rollbacks) e
[endpoint de rollback](https://api-docs.render.com/reference/rollback-deploy).

## Imagem única: decisão e migração proposta

**Decisão atual:** preservar os dois serviços Git-backed ativos. A implementação
Render promove SHA, não digest. O build GitHub valida o Dockerfile, mas seu tarball
não alimenta o Render. Tags de imagem base mutáveis permitem diferenças mesmo
com o mesmo código e lockfile. Nenhum digest de registry foi medido neste ensaio.

**Possível no Render, ainda não implantado:** utilizar serviços image-backed
alimentados por GHCR. Não basta passar `imageUrl` aos atuais serviços Git-backed.
A adoção exige configurar a origem de imagem, acesso ao registry, retenção e
validar a transição de serviço/URL. Não substituímos produção para realizar esse
aperfeiçoamento. O caminho AWS já descrito no projeto promove uma URI ECR por
digest, mas está desativado e não serve como evidência de execução.

Fluxo futuro, sem rebuild por ambiente:

1. Testar o código e construir **uma vez**, `linux/amd64`, com rótulo
   `org.opencontainers.image.revision=SHA`. Validar usuário não root, ausência de
   secrets e arquivos estáticos nessa imagem. Fixar também a base por digest,
   atualizada periodicamente com revisão de segurança.
2. No job de publicação de `main`, usar `GITHUB_TOKEN` com `packages: write` para
   publicar no GHCR; PRs permanecem sem essa permissão e sem deploy. Tag amigável
   `sha-SHA` facilita consulta, mas nunca determina a promoção.
3. Obter o digest do manifesto retornado pelo push/build, por exemplo output
   `digest` de `docker/build-push-action` devidamente fixada por SHA. Não confundir
   ID local de imagem (`docker inspect .Id`) ou checksum do tar com digest do
   manifesto no registry.
4. Exportar URI `ghcr.io/renatoxdev/elo-saude@sha256:DIGEST` como output do job e
   registrá-la com SHA/run ID. Para imagem privada, configurar credencial de
   leitura no Render; nunca embuti-la na imagem. Acesso ao pacote não é garantido
   apenas porque o repositório é público.
5. Criar/validar staging image-backed com as mesmas configurações e banco de
   staging. Implantar a URI imutável pela API de deploy (`imageUrl`), aguardar
   `live`, conferir a referência e executar smoke. Nenhum `docker build` aqui.
6. Após aprovação e janela de transição, produção recebe **a mesma URI**, passada
   como output da etapa validada, sem resolver novamente tag. Comparar ambos os
   digests e abortar se divergirem. Preservar os serviços anteriores até validar
   o retorno, sem permitir escritores/migrations concorrentes durante a troca.
7. Reter ao menos as últimas dez imagens aprovadas por 30 dias (política proposta),
   nunca remover digest ativo ou reservado para rollback. Reversão usa URI
   anterior ainda acessível no registry. Não usar `latest` para rollback.

Essa proposta agrega registry, permissões e gestão de retenção, mas dispensa
Kubernetes ou outra camada de orquestração. A promoção por SHA atual é mantida
até haver uma transição testada. [Imagens pré-construídas no Render](https://render.com/docs/deploying-an-image).

## Monitoramento e alertas — proposta não instalada

Começar com verificação externa de disponibilidade, métricas do provedor e os
logs JSON existentes (`X-Request-ID`, status e duração), sem instalar uma stack
completa. Coletar taxas por rota normalizada/status, p50/p95, quantidade de
requisições, 5xx, 401/429, reinícios, CPU/memória, conexões/armazenamento PostgreSQL
em canal restrito. Não incluir nomes, endereços, JWT, query strings ou senhas em
labels/logs. Metas abaixo são iniciais e precisam de baseline de uso real.

| Condição proposta | Severidade | Ação |
|---|---|---|
| Readiness falha em 3 sondagens de 1 minuto, após tolerância de cold start | Crítico | Confirmar processo, conectividade e PostgreSQL; suspender promoção |
| 5xx > 5% em 5 min, com pelo menos 20 requisições | Crítico | Correlacionar deploy/request ID, avaliar rollback compatível |
| Erros repetidos de conexão com banco por 3 min | Crítico | Verificar serviço Neon, credenciais e limite de conexões |
| Backup ausente por mais de 26 h ou falha de integridade | Crítico | Corrigir job/armazenamento e realizar cópia validada |
| p95 > 2 s por 10 min, pelo menos 20 requisições, excluindo despertar | Warning | Separar espera de banco, ViaCEP e saturação |
| Memória ou conexões > 80% por 10 min; armazenamento > 80% | Warning | Investigar consumo e projetar capacidade |
| Recurso > 95% ou reinícios recorrentes com indisponibilidade | Crítico | Conter causa e ajustar capacidade |
| 401/429 > 3 vezes baseline por 10 min | Warning | Investigar abuso/cliente mal configurado; não bloquear só por volume |

Enviar alertas ao responsável pelo serviço por canal configurado, com ambiente,
horário, runbook e link para métricas. Deduplicar, sinalizar recuperação e testar
notificação mensalmente. Ainda não há monitor externo, alerta ou plantão
provisionado; não declarar SLA. No plano gratuito, sondagens também afetam consumo
e suspensão; alinhar frequência ao orçamento antes de ativá-las.

## Backup PostgreSQL — proposta não executada

Meta inicial: RPO de até 24 h para backup lógico diário e RTO de até 4 h,
**não medidos**. Para reduzir RPO, habilitar/verificar a janela de recuperação
Neon disponível no plano contratado; não pressupor retenção específica do Free.
PITR do provedor complementa, mas não substitui uma cópia independente.

Agendar `pg_dump` diário em formato custom com cliente PostgreSQL 18 para os
bancos Neon 18 (um cliente 17 não serve para dump de servidor 18).
Credenciais em secret manager/arquivo de serviço PostgreSQL com permissão 0600,
TLS e role de backup com acesso suficiente, sem valores em argumentos/logs.
Armazenar cópia criptografada em bucket privado separado do banco e da aplicação,
preferencialmente outra conta, com permissões mínimas e gestão de chaves separada.
Proposta de retenção: 7 cópias diárias, 4 semanais e 3 mensais, a revisar com
necessidade de negócio e proteção de dados. Não versionar dumps no GitHub nem
armazená-los no filesystem efêmero Render.

O job deve conferir código de saída, tamanho não vazio, checksum, inventário do
arquivo e upload; registrar apenas metadados. Alertar falha e ausência de execução.
Uma cópia existente não prova restaurabilidade: ensaio mensal e após migrations
relevantes, registrando duração, versão, integridade, RPO/RTO obtidos e limpeza.

## Restauração isolada — procedimento futuro

1. Selecionar backup e ponto de recuperação; verificar checksum e acesso às chaves.
2. Criar banco/projeto **novo e isolado**, sem apontar o serviço de produção para
   ele. Conferir explicitamente host/database destino e impedir credenciais de
   escrita em produção no processo de restauração.
3. Usar cliente compatível para `pg_restore --exit-on-error --no-owner --no-acl`
   no banco vazio; conferir extensões, proprietários e permissões necessárias.
   Recriar roles/permissões separadamente, sem assumir que `pg_dump` as preserva.
4. Comparar schema/migrations, contagens e vínculos; validar aplicação compatível,
   login e CRUD com usuário temporário, sem enviar mensagens/pagamentos externos.
   Medir duração e perda máxima de dados correspondente ao backup.
5. Registrar resultado e falhas; apagar ambiente temporário conforme retenção de
   evidências e regras de proteção de dados. Acesso restrito também vale para cópias.
6. Uma troca real de produção exige plano específico, aprovação, contenção de
   escritas e reconciliação. **Nunca usar produção como destino de teste.**

Alternativamente, testar recuperação histórica Neon em branch/projeto separado,
dentro da janela disponível. Nenhum restore de banco foi realizado neste trabalho.
[Recuperação Neon](https://neon.com/docs/introduction/branching).

## Cache e throttling com múltiplas réplicas — análise

Não há `CACHES` explícito: Django usa `LocMemCache`, por processo. ViaCEP armazena
apenas endereços válidos por uma hora. `ScopedRateThrottle` usa o mesmo cache para
auth (`10/min`) e CEP (`30/min`). Com A e B, cada processo tem sua própria contagem;
o limite observado pode crescer conforme número de workers/réplicas e reinícios
apagam estado. Isso ocorre inclusive com vários workers na mesma máquina.

Evolução proposta: Redis gerenciado, privado, com TLS/autenticação e namespaces
separados por ambiente. Cache de CEP usa TTL de uma hora; evitar cache negativo de
falhas transitórias. Manter apenas dados públicos de CEP e eventualmente schema
estático versionado; não cachear JWT, senhas, consultas, contatos ou respostas
personalizadas sem requisitos de autorização, invalidação e retenção definidos.
Cache indisponível pode resultar em consulta direta ao ViaCEP, mantendo timeout e
limite de carga; testar esse comportamento, pois trocar backend sozinho não o garante.

Redis compartilhado elimina contagens isoladas, mas **não torna o throttle padrão
do DRF atômico**. Para limite consistente sob concorrência, implementar algoritmo
com atualização e expiração atômicas (token bucket/sliding window em script Lua)
ou usar gateway com quota compartilhada. Testar requisições simultâneas em duas
réplicas, expiração, reconexão e `429`/`Retry-After`. Separar memória/política de
eviction das quotas e do cache descartável, evitando apagar limites por pressão.

Identidade deve usar usuário autenticado ou IP obtido de topologia validada. Hoje
`NUM_PROXIES=0` evita confiar em `X-Forwarded-For` forjado, mas atrás do proxy pode
agrupar clientes pelo IP do intermediário. Antes de mudar, verificar quantos proxies
confiáveis existem e como removem cabeçalhos recebidos. Não aceitar IP arbitrário.

Para auth, falha do limitador deve ter política explícita (por exemplo `503`
controlado com alerta, mantendo refresh/relogin em consideração), evitando bypass
silencioso. Redis não substitui proteção contra DDoS/abuso na borda. Ainda não foi
adicionado Redis: o porte atual não justifica operação e custo novos apenas para
a demonstração. [Limites de concorrência do DRF](https://www.django-rest-framework.org/api-guide/throttling/).

Referência para compatibilidade de backups: [pg_dump PostgreSQL 18](https://www.postgresql.org/docs/18/app-pgdump.html).

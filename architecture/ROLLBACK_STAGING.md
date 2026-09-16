# Ensaio de rollback em staging — 16/09/2026

**Executado com sucesso**, exclusivamente em `elo-saude-staging`. Produção foi
consultada apenas pela API administrativa para confirmar o mesmo deploy ativo;
nenhum teste HTTP, escrita de dados ou publicação em produção foi feito.

## Versões e resultados reais

| Fase | Commit completo | Deploy | Live em UTC | Smoke |
|---|---|---|---|---|
| baseline | e1fc9bbef8c3919e1f90240ece3c81084753d105 | dep-dal85pdbedkc73bk0k90 | 2026-09-16T11:53:09.137057Z | 15/15 |
| rollback | bd5f91e749bd2babb83b1b465f659109fcc7055d | dep-dalbjjjm8hqs73907eu0 | 2026-09-16T15:47:32.537444Z | 15/15 |
| restored | e1fc9bbef8c3919e1f90240ece3c81084753d105 | dep-dalbkg740ujc73decg00 | 2026-09-16T15:49:21.991931Z | 15/15 |

Fim do ensaio: `2026-09-16T15:50:10.151588+00:00`. O deploy anterior usado como alvo foi
`dep-dal0vvm7bikc73dvsvk0`. O retorno usou o artefato do deploy inicial
`dep-dal85pdbedkc73bk0k90`, gerando um novo ID de deploy.

Os dois commits diferem **somente em documentação**. Não houve mudança de schema,
configuração de runtime ou migrations no intervalo. O ensaio valida a mecânica de
rollback e a continuidade funcional; não simula reversão de migration destrutiva.

## Procedimento executado

1. Consultados serviço e deploys via API Render; confirmados nome de staging,
   URL, branch/repositório e Auto-Deploy desligado.
2. Confirmada ausência de workflows em execução/fila. Salvo valor `true` de
   `RENDER_DEPLOY_ENABLED`, alterado temporariamente para `false`.
3. Criado usuário temporário não administrativo no banco exclusivo de staging,
   com credenciais carregadas em memória. Executado smoke inicial.
4. Enviado `POST /v1/services/{stagingServiceId}/rollback` com `deployId` do
   deploy anterior. Consultado o novo deploy até `live` e conferido SHA completo.
5. Repetido smoke autenticado. Solicitado rollback para o artefato inicial,
   aguardado `live`, conferido SHA e repetido smoke.
6. Removidos dados e usuário temporários e seus registros de tokens. Confirmada
   limpeza. Restaurado `RENDER_DEPLOY_ENABLED=true` após validação final.

Foram **45 verificações HTTPS** (15 por fase), todas aprovadas:

| Verificação por fase | Resultado |
|---|---|
| Liveness e readiness | 200, JSON exatamente `{"status":"ok"}` em ambos |
| Swagger e OpenAPI | 200; schema contém rota de profissionais |
| Listagem sem token | 401 |
| Login JWT com usuário temporário | 200 |
| Criar, buscar por ID e alterar profissional | 201, 200, 200 |
| Criar consulta e filtrar por profissional | 201, 200; ID criado presente |
| Excluir profissional com consulta | 409 |
| Excluir consulta e profissional temporários | 204, 204 |
| Revogar refresh token | 200 |

Os [registros JSON sanitizados](evidence/rollback-staging-2026-09-16.json) incluem
horário e status por requisição, IDs e SHAs. Não incluem Bearer, senhas, strings de
conexão ou dados de cadastro. `status=live` nas fases é o estado observado naquele
momento; versões anteriores aparecem depois como `deactivated` no Render.

## Escopo e limitações

- Digest Docker implantado: **não medido/disponibilizado neste registro**. Serviços
  atuais são Git-backed; identificamos commits e artefatos pelo ID do deploy.
- Banco não foi restaurado e migrations não foram revertidas.
- Produção permaneceu em `bd5f91e749bd2babb83b1b465f659109fcc7055d`, deploy `dep-dal10kdg1s2s73drtogg`.
- O estado final do ensaio é o retorno a `e1fc9bb`. Publicações posteriores de
  documentação via CI são operações separadas, não alteram a evidência histórica.
- Repetição e critérios de interrupção: [runbook](OPERATIONS.md#rollback-controlado-apenas-staging-no-ensaio).

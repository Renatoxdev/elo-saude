# Proposta de integração Asaas — bônus, não implementado

A API atual não processa pagamentos. Esta é uma proposta de extensão; não foram
criados endpoints, modelos financeiros, mocks executáveis ou chamadas ao Asaas.
A implementação começaria em sandbox, com regras de cobrança definidas com o
negócio e sem misturar pagamento com disponibilidade do CRUD de consultas.

## Limite do módulo e contrato proposto

Um módulo `payments` dependeria de um adapter, não de chamadas HTTP nas views de
consultas. Contrato conceitual: `create_charge(order_id, amount, customer_ref)` e
`get_charge(external_id)`. Um fake determinístico implementaria o contrato nos
testes, inclusive timeout, indisponibilidade e cobrança já existente.

Persistência proposta: ordem interna com UUID único, valor em Decimal, moeda,
estado e vínculo com consulta; identificador externo único após confirmação;
eventos recebidos com `provider_event_id` único e estado de processamento.
Não adicionar dados clínicos ao payload do gateway. Identificação do pagador
precisa de requisitos próprios e coleta mínima; não inferir que o profissional
cadastrado seja o cliente pagante.

## Criação e reconciliação

Criar ordem interna em transação e registrar intenção durável de envio (outbox
no PostgreSQL). Um processador simples pode consumir essa tabela; não é necessário
introduzir broker antes de haver volume. Cliente HTTP deve ter timeout, limites
de resposta e erro sanitizado. Configurar secrets separados por ambiente.

Uma restrição única por operação evita duplicação local. Após timeout de criação,
o resultado remoto é desconhecido: marcar para reconciliação e consultar o
provedor antes de repetir. Não assumir suporte a header genérico de idempotência
sem confirmar o endpoint Asaas escolhido. Usar referência externa conforme
contrato documentado e confirmar unicidade por reconciliação; referência sozinha
não prova deduplicação no provedor. Retries de leituras podem usar backoff/jitter.

## Webhook e consistência

HTTPS com `asaas-access-token` comparado ao segredo configurado, sem logar o
header. Validar tamanho, formato e tipo de evento. Persistir evento de forma
durável antes de retornar `200`; duplicatas já persistidas recebem `200` sem
reaplicar a transição. Se a persistência falhar, não confirmar sucesso.

Processamento transacional, com identificador de evento único e bloqueio da
ordem durante transição. Eventos fora de ordem exigem regras explícitas e
reconciliação com o estado remoto, sem regredir cobrança paga para pendente
apenas pela ordem de chegada. Valor, moeda e vínculo precisam coincidir com a
ordem. Processador deve retentar eventos persistidos ainda pendentes e alertar
falhas definitivas; não depender de nova entrega após responder `200`.

## Validação antes de qualquer operação real

Testar fake: criação duplicada, timeout após sucesso remoto, token de webhook
inválido, evento duplicado/fora de ordem, falha de banco e reprocessamento.
Depois validar contrato no sandbox. Política de cancelamento, estorno, split,
conciliação e retenção de dados é decisão de negócio anterior ao uso real.
Nada disso modifica ou bloqueia a API existente nesta entrega.

Referências oficiais consultadas em 16/09/2026:
[recepção de eventos](https://docs.asaas.com/docs/receba-eventos-do-asaas-no-seu-endpoint-de-webhook)
e [FAQ de webhooks](https://docs.asaas.com/docs/faq-de-webhooks).

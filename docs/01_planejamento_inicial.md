# Planejamento inicial — PSP8
Registrado em 21/10/2026, antes da coleta e da análise.

## Tema
Priorização de melhorias logísticas a partir dos atrasos de entrega no comércio eletrônico brasileiro.

## Problema e decisão
Um gestor de operações precisa decidir onde investigar e priorizar melhorias no cumprimento do prazo prometido. O MVP fornece indicadores de atraso e concentrações por destino e período, distinguindo risco relativo e volume absoluto. Trata-se de diagnóstico retrospectivo; não estima efeito causal de intervenções.

## Hipótese de trabalho
Os atrasos não se distribuem uniformemente entre destinos e períodos, e pedidos atrasados apresentam maior frequência de avaliações baixas. A hipótese será confrontada com resultados observados; associação não implica causalidade.

## Perguntas originais
1. Qual a proporção de pedidos entregues após a data prometida e qual a magnitude desses atrasos?
2. Quais estados de destino concentram mais atrasos e quais têm maiores taxas, considerando o volume de pedidos?
3. Como a taxa de atraso e o tempo de entrega evoluem por mês de compra?
4. Como o prazo entre compra e entrega se distribui entre aprovação, preparação/entrega à transportadora e transporte final?
5. Qual a associação entre atraso e avaliação baixa do cliente (notas 1 ou 2)?

## Critérios definidos antes dos resultados
- Unidade principal: um pedido; itens e avaliações serão consolidados antes de qualquer junção para evitar multiplicação de linhas.
- Atraso: data civil de entrega posterior à data civil estimada; entregas no dia prometido são pontuais.
- População analítica de pontualidade: pedidos entregues com datas válidas de compra, promessa e entrega, sem entrega anterior à compra.
- Pedidos sem desfecho de entrega não serão classificados como pontuais; sua exclusão e contagem serão documentadas.
- Comparações por estado: mostrar n e intervalo de Wilson de 95%; destacar grupos com pelo menos 100 pedidos. Limite operacional, não garantia de representatividade.
- Etapas temporais: somente sequências completas e cronologicamente consistentes; relatar a cobertura.
- Avaliações múltiplas: última resposta por pedido, com desempate determinístico; avaliar também duplicidade e cobertura.
- Estatística: distribuição, mediana, percentil 90, taxas, intervalos de Wilson e diferença de proporções com intervalo de Newcombe. Intervalos são aproximações condicionais, não extrapolação para todo o comércio eletrônico.
- Não alegar representatividade nacional, causalidade, economia monetária realizada ou validação com usuários sem evidência.

## MVP e critério de aceitação
Pipeline reproduzível de coleta, tratamento, modelagem, persistência em tabelas Delta no Databricks e análise das cinco perguntas. Entrega requer execução real na nuvem e GitHub público; validação local não substitui essas etapas.

## Valor e limites
Usuário-alvo: gestor de operações/logística. Métrica de utilidade: cinco perguntas com indicadores reproduzíveis e prioridades explícitas; desejabilidade será apenas proposta, pois não há entrevista com gestor nesta etapa. Viabilidade técnica depende da execução real. Custo: usar a edição gratuita dentro das cotas; esforço de manutenção e migração devem ser discutidos, sem prometer custo zero para produção.

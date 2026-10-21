# Evidências de execução

Em 21/10/2026, o autor importou e executou o notebook no Databricks Free Edition. A leitura da interface confirmou 11 células de código concluídas com sucesso, incluindo persistência e validação, e resultados SQL compatíveis com a execução local. Não foram criadas capturas sintéticas.

Pendente de anexação: exportação do notebook com saídas, capturas da persistência e do Catalog. Não usar os gráficos locais como prova isolada de armazenamento na nuvem. Os CSV de validação são produzidos pela execução no volume do projeto e devem ser exportados diretamente.

Correspondência necessária:
- Persistência: tabela `verification` com origem/Delta e mensagem de verificação.
- Integridade: 99.441 pedidos distintos, 96.470 elegíveis e 6.534 atrasos.
- Q2: consulta `gold_por_uf`.
- Q3: consulta `gold_por_mes`.
- Q4: consulta `gold_etapas`.
- Q5: consulta `gold_avaliacoes`.

Antes de publicar screenshots, ocultar e-mail e dados de conta que não sejam necessários à avaliação. Preservar integralmente os resultados e identificar qualquer ocultação de interface.

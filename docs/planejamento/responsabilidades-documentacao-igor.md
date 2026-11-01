# Responsabilidades de Documentação: Igor

**Status:** decisão final do grupo, registrada em [ADR 0007](../decisions/0007-divisao-equipe-final.md).

Este documento detalha, em forma de regras práticas, o que a
responsabilidade de "documentação do projeto" significa no dia a dia,
para que fique claro o que fazer sem precisar perguntar toda vez.

---

## 1. Google Drive: pasta compartilhada do TCC

- Link oficial (já no README raiz, seção "Links Úteis"):
  [Pasta Partilhada no Google Drive](https://drive.google.com/drive/folders/1x9B_vlEw8Yn10jC9kYOUhRTUJoWjrQXT?usp=drive_link).
- **Regra:** manter essa pasta organizada por categoria (ex.: `01-atas/`,
  `02-tcc-escrita/`, `03-referencias/`, `04-apresentacoes/`), não como
  uma lista solta de arquivos soltos por data de upload.
- Qualquer capítulo de TCC, ata, ou material de apresentação gerado pelo
  grupo deve ter uma cópia (ou o original) organizada nessa pasta;
  Igor é quem garante que isso aconteça, cobrando de quem gerou o
  material se necessário.
- Se a estrutura de pastas do Drive mudar, atualizar a descrição dela
  neste documento (Seção 1) para o restante do grupo saber onde achar
  as coisas.

## 2. Figma: protótipos de UI

- Link a preencher em [README raiz](../../README.md), seção "Links
  Úteis do Projeto" (hoje está como placeholder). **Primeira tarefa do
  Igor nesta frente: criar o arquivo Figma do projeto e colocar o link
  lá.**
- **Regra:** manter o Figma organizado por tela (nomeando os frames de
  forma consistente com as telas reais de `app/src/screens/` (Alertas,
  Diagnóstico, Histórico, Financeiro, Login), para que Amanda (e Igor,
  quando estiver apoiando o `app/`) trabalhem a partir de uma referência
  visual sempre atualizada.
- Protótipos descartados ou versões antigas devem ser movidos para uma
  página separada dentro do próprio arquivo Figma (ex.: "Arquivo/Descartado"),
  não apagados; útil para justificar decisões de design na banca, se
  perguntado.

## 3. Organização de reuniões

- **Agendamento:** Igor é quem propõe data/horário das reuniões
  periódicas do grupo (alinhadas ao ritmo de sprints de 2 semanas,
  ver README raiz, seção de Metodologia) e confirma presença de todos.
- **Pauta (antes da reunião):** enviar uma pauta curta no grupo (Discord)
  com os pontos a discutir, com pelo menos algumas horas de
  antecedência. Pontos recorrentes de pauta sugeridos:
  - Decisões pendentes em aberto (ver `docs/planejamento/divisao-equipe-e-roadmap.md`,
    Seção 1).
  - Status de cada camada (`ml/`, `app/`, `cloud/`/`infra/`/`edge/`).
  - Bloqueios que alguém esteja enfrentando.
- **Ata (durante/depois da reunião):** registrar em `docs/atas/`,
  criando a pasta na primeira ata, com a convenção de nome
  `AAAA-MM-DD-assunto-principal.md`. Uma ata mínima deve
  conter: data, presentes, decisões tomadas, e próximos passos por
  pessoa.

## 4. Registro de decisões técnicas e de processo (ADRs)

- Toda decisão de arquitetura ou de processo relevante, mesmo que
  pequena, deve virar um ADR novo em [`docs/decisions/`](../decisions/README.md),
  seguindo a convenção `NNNN-titulo-curto-em-kebab-case.md`.
- **Regra prática:** se numa reunião ou conversa alguém disser "ok,
  ficou decidido que vamos fazer X assim", isso é sinal de que precisa
  virar um ADR. Igor é quem cria esse arquivo (pode pedir ajuda de quem
  tomou a decisão para preencher os detalhes técnicos, mas a
  responsabilidade de o ADR existir é dele).
- Exemplos já registrados: [0001](../decisions/0001-camera-module-3.md)
  (câmera), [0002](../decisions/0002-frontend-framework-pendente.md)
  (framework de frontend), [0003](../decisions/0003-autenticacao-dual.md)
  (autenticação), [0007](../decisions/0007-divisao-equipe-final.md)
  (divisão de equipe).

## 5. Manutenção do roadmap e do calendário

- Manter [`docs/planejamento/divisao-equipe-e-roadmap.md`](divisao-equipe-e-roadmap.md)
  atualizado conforme decisões mudam: é o documento de referência de
  "quem faz o quê" e "o que falta decidir".
- Preencher [`infra/calendar/sincronizacao.md`](../../infra/calendar/sincronizacao.md)
  assim que a data da banca for confirmada pela coordenação.
- Manter [`docs/planejamento/lista-compras-hardware.md`](lista-compras-hardware.md)
  atualizada com o status de cotação/compra de cada item (isso pode ser
  preenchido em conjunto com quem estiver comprando, mas Igor garante
  que a tabela não fique desatualizada).

## 6. Escrita acadêmica do TCC

- Igor não escreve necessariamente todo o conteúdo técnico do TCC
  (cada área deve redigir a parte que domina, ex.: João documenta a
  metodologia de ML, Higor documenta a arquitetura de backend), mas é
  responsável por:
  - Manter a estrutura de capítulos organizada em
    [`docs/tcc/`](../tcc/README.md) e no Drive.
  - Cobrar/coordenar prazos de entrega de cada parte com quem for
    escrevê-la.
  - Garantir que os pontos que o Blueprint pede para serem tratados
    **proativamente** na banca (ex.: o risco estatístico do split
    70/15/15, ver `ml/README.md`) realmente virem texto, e não fiquem
    só na cabeça de quem discutiu isso uma vez.

## 7. Apoio ao `app/` nas primeiras semanas (responsabilidade temporária)

- Amanda é a responsável técnica pelo `app/`: é ela quem decide o que
  o Igor vai fazer nessa frente, não este documento.
- **Regra de processo:** antes de começar qualquer tarefa de frontend,
  Igor e Amanda alinham juntos (rapidamente, pode ser numa conversa
  curta) o que exatamente ele vai implementar, para não haver
  sobreposição de trabalho ou retrabalho.
- Essa responsabilidade é temporária: dura enquanto o `app/` estiver
  arrancando. Quando Amanda considerar que não precisa mais de apoio
  direto, Igor passa a dedicar 100% do tempo à documentação (Seções
  1-6 acima).

---

## Checklist de início rápido para o Igor

- [ ] Criar o arquivo Figma do projeto e atualizar o link no README raiz.
- [ ] Organizar a pasta do Drive em subpastas (atas, TCC, referências, apresentações).
- [ ] Depois da reunião, criar a primeira ata em `docs/atas/`.
- [ ] Alinhar com a Amanda a primeira tarefa de apoio no `app/`.

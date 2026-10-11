# app: Frontend / Aplicativo

**Framework: Expo (React Native)**, ver
[ADR 0002](../docs/decisions/0002-frontend-framework-pendente.md).

**Responsável pela camada:** Amanda. A integração com o backend
(serviços, autenticação, saída dos mocks) foi feita pelo Higor, como
combinado em [ADR 0007](../docs/decisions/0007-divisao-equipe-final.md).

Referência arquitetural: [**Blueprint v4.0**](../docs/architecture/blueprint-v4.md).

## Papel desta camada

- Aplicativo usado pelo produtor rural: início, diagnóstico, histórico,
  alertas, financeiro e perfil.
- Autenticação via JWT mais refresh token, consumindo os endpoints do
  FastAPI. Renovação automática: um 401 em rota autenticada dispara uma
  renovação e repete a requisição, uma única vez.
- **Nunca** acessa o Supabase diretamente, sempre via API no Railway. A
  imagem do diagnóstico chega como signed URL já pronta na resposta.

## Origem dos dados, tela por tela

Isto é o que mais mudou em 2026-10-11: as telas saíram dos mocks.

| Tela | Fonte | Observação |
|---|---|---|
| Início | `GET /leituras` e `GET /diagnosticos` | O card de situação sanitária conta diagnósticos reais |
| Diagnóstico | `GET /diagnosticos` | Imagem por signed URL; mostra o escopo do modelo no pé |
| Histórico | `GET /leituras` e `GET /diagnosticos` | Filtro por estufa usa o `device_id` de verdade |
| Alertas | `GET /alertas`, `PATCH /alertas/{id}/lido` | Estado "lido" persiste no banco |
| Perfil | `GET /usuarios/me`, `GET /dispositivos` | |
| Vincular dispositivo | `POST /dispositivos/vincular` | Código `ECO-XXXX-XXXX` da etiqueta |
| Login, cadastro, confirmação, recuperação | `/auth/*` | |
| **Financeiro** | **AsyncStorage local** | **Único mock restante, por decisão de escopo: ver abaixo** |

**Com o dispositivo ainda sem captura ligada, o normal é as telas de
diagnóstico aparecerem VAZIAS.** Esse é o comportamento correto. Vazio
diz a verdade; mock, não. Antes desta mudança, o app mostrava
temperatura real de um lado e folha inventada do outro, o que é pior do
que não mostrar nada.

**Financeiro** continua em `AsyncStorage` de propósito: o controle de
gastos nunca foi parte do escopo de monitoramento fitossanitário e serve
de demonstração de interface. Consequência assumida: reinstalar o app
apaga os gastos, e outro aparelho na mesma conta não os vê.

## Estrutura

```
app/
└── src/
    ├── screens/          # Welcome, Login, Cadastro, VerificarEmail,
    │                     # RecuperarSenha, Dashboard, Diagnostico,
    │                     # Historico, Alertas, Financeiro, Perfil,
    │                     # VincularDispositivo
    ├── navigation/       # React Navigation
    ├── services/         # cliente HTTP (JWT + renovação) e uma camada
    │                     # por recurso: auth, leituras, diagnosticos,
    │                     # alertas, dispositivos, perfil, gastos
    ├── domain/           # doencas.ts: vocabulário de condições
    │                     # fitossanitárias e escopo do modelo
    ├── components/       # cards, gráficos, estados de carga e erro
    ├── hooks/            # useCarregamentoAssincrono (loading/erro/refresh)
    ├── config/           # env.ts (variáveis EXPO_PUBLIC_*)
    ├── mocks/            # só gastos.json, ver acima
    └── notifications/    # Expo Notifications
```

## Duas armadilhas desta camada que custaram tempo

**1. `process.env` tem que ser acesso ESTÁTICO.** O Metro substitui
`process.env.EXPO_PUBLIC_API_URL` em tempo de build, por texto. Acesso
dinâmico (`process.env[chave]`) não é substituído, então a variável
chega `undefined` **só no build publicado**: funciona no Expo Go e
quebra no APK, com um "Something went wrong" sem pista. Ver
`src/config/env.ts`, que acessa cada variável de forma estática de
propósito.

**2. Vocabulário diferente nas duas pontas.** O backend grava severidade
de alerta como `alta` e `media`; as telas foram desenhadas com
`critico`, `cuidado` e `informativo`. A tradução fica em
`src/services/alertas.ts`, com valor padrão: uma severidade
desconhecida degrada para `informativo` em vez de quebrar a lista ao
procurar uma cor que não existe.

## Atualização e build

O APK em uso aponta para o canal `preview` do EAS Update. Correção de
JavaScript chega sem reinstalar: o app baixa numa abertura e aplica na
seguinte. Mudança que toque código nativo exige build novo
([ADR 0014](../docs/decisions/0014-deploy-railway-e-gate-de-ci.md)).

Não existe build de iOS: ninguém do grupo tem iPhone, e a demonstração
é Android mais Expo Go.

## Verificação antes de publicar

```bash
cd app
npx tsc --noEmit    # não existe suíte de testes nesta camada
```

## Pendências

- Notificação só funciona com o app aberto, por decisão registrada em
  [ADR 0012](../docs/decisions/0012-notificacao-local-sem-push.md).
- A Amanda precisa aceitar o convite da organização no Expo: o
  `projectId` mudou e sem isso ela não consegue publicar atualização.

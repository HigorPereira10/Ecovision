# ADR 0012: Notificação local em vez de push de servidor

**Status:** Decidido (2026-10-11). Limitação conhecida e assumida, não
pendência esquecida.

## Contexto

O app tem notificações funcionando: `expo-notifications` instalada,
permissão pedida, canal Android configurado, e `verificarNovosAlertasNaoLidos`
(`app/src/services/notificacoes.ts`) disparando notificação para alerta
não lido que ainda não foi notificado naquele aparelho.

O que **não** existe é push vindo do servidor. O token do Expo é
registrado no aparelho e morre ali: nenhuma rota da API o recebe, nenhuma
tabela o guarda, nada observa alertas novos para disparar envio.

A consequência precisa estar dita sem rodeio: **o produtor só é avisado
quando abre o app.** Com o app fechado, uma estufa a 40 °C não gera
aviso nenhum.

## Decisão

Manter notificação **local**, disparada pelo próprio aparelho ao focar a
tela de Alertas, e declarar essa limitação na documentação e na banca,
em vez de implementar push pela metade.

## Motivo

Push de servidor exige três coisas que o sistema hoje não tem:

1. **Guardar o token do Expo por usuário.** Tabela nova, rota nova, e o
   token muda (reinstalação, limpeza de dados, troca de aparelho), então
   precisa de atualização e de limpeza de token morto.
2. **Alguém observando alertas novos.** O [ADR 0008](0008-deteccao-dispositivo-inativo.md)
   já decidiu que não há job em background: o Blueprint v3.0 fixou **1
   único worker** no Railway, e o alerta de dispositivo inativo é
   calculado sob demanda justamente por isso. Push exigiria contrariar
   essa decisão ou acoplar o envio ao `POST /diagnostico`, que é o
   caminho crítico do Pi: uma falha na API de push do Expo atrasaria ou
   derrubaria o recebimento da captura.
3. **Dependência de um serviço externo a mais** (Expo Push), somada a
   Railway, Supabase e Brevo, cada uma com cota e modo de falha próprio.

Para um protótipo de TCC com um dispositivo, o custo é alto e o ganho de
nota é baixo: a banca avalia a arquitetura e a honestidade sobre os
limites dela, não a quantidade de integrações.

## O que fica implementado

| Comportamento | Existe |
|---|---|
| Notificação ao focar a tela de Alertas, para alerta não lido | Sim |
| Controle de "já notifiquei este alerta" por aparelho (AsyncStorage) | Sim |
| Notificação com o app fechado | **Não** |
| Notificação em outro aparelho da mesma conta | **Não** |
| Botão de sino que dispara notificação de demonstração | Sim, só em `__DEV__` ou conta administrador |

**Sobre o sino:** ele é ferramenta de apresentação, não funcionalidade.
Para o produtor, parecia um ícone comum de notificações, e quem tocasse
receberia um alerta inventado sobre a própria estufa. Por isso aparece
só durante o desenvolvimento (`__DEV__`) ou para quem estiver numa conta
de papel `administrador`, que o grupo usa na banca. As duas condições
existem porque `__DEV__` desaparece em build de produção, inclusive para
o grupo.

**Detalhe que mudou com a saída do mock:** o controle de "já notifiquei"
passou a ser indexado pela **chave** do alerta, não pelo id numérico. O
alerta sintético de dispositivo inativo ([ADR 0008](0008-deteccao-dispositivo-inativo.md))
chega com `id: null`, e `null` como identificador faria todos os alertas
sem id colidirem num só.

## O que seria necessário para ter push de verdade

Registrado para a seção de trabalhos futuros do TCC:

1. `POST /usuarios/me/push-token`, guardando token por usuário e
   aparelho, com remoção quando o Expo reporta token inválido.
2. Disparo de envio **assíncrono** em relação ao `POST /diagnostico`,
   para não acoplar o caminho do Pi à API de push.
3. Tratamento de cota e de erro do Expo Push, com retentativa.
4. Decidir o que acontece quando o produtor tem dois aparelhos e lê o
   alerta em um deles.

## Implementação atual

- `app/src/services/notificacoes.ts`
- `app/src/notifications/pushNotifications.ts` (registro do token, hoje
  sem destino no servidor)
- `app/src/screens/AlertasScreen.tsx` (verificação ao focar a tela)

# app

Aplicativo Android do EcoVision, desenvolvido com Expo e React Native. O
produtor acompanha a situação sanitária da planta, as séries de
temperatura e umidade, os diagnósticos e os alertas de cada dispositivo
vinculado à sua conta.

## Funcionamento

- Autenticação por JWT com token de renovação: uma resposta 401 em rota
  autenticada dispara uma renovação e repete a requisição uma única vez.
- Todo acesso a dados passa pela API; o aplicativo não acessa o Supabase.
  As imagens chegam como URLs assinadas.
- Os alertas não lidos geram notificação local quando o aplicativo
  consulta a API; não há notificação push enviada pelo servidor.

| Tela | Origem dos dados |
|---|---|
| Início | `GET /leituras` e `GET /diagnosticos` |
| Diagnóstico | `GET /diagnosticos` |
| Histórico | `GET /leituras` e `GET /diagnosticos` |
| Alertas | `GET /alertas` e `PATCH /alertas/{id}/lido` |
| Perfil | `GET /usuarios/me` e `GET /dispositivos` |
| Vincular dispositivo | `POST /dispositivos/vincular` |
| Login, cadastro, confirmação e recuperação de senha | `/auth/*` |
| Financeiro | Armazenamento local do aparelho (AsyncStorage) |

O módulo financeiro é complementar ao monitoramento: os dados ficam só no
aparelho, não são sincronizados e se perdem se o aplicativo for
desinstalado.

## Estrutura

```
app/
├── App.tsx
└── src/
    ├── screens/         # telas
    ├── navigation/      # navegação (React Navigation)
    ├── services/        # cliente HTTP e um módulo por recurso da API
    ├── domain/          # condições fitossanitárias e escopo do modelo
    ├── components/      # cartões, gráficos e estados de carga e erro
    ├── hooks/           # carregamento assíncrono com atualização
    ├── config/          # variáveis EXPO_PUBLIC_*
    ├── theme/           # cores
    ├── utils/           # formatação e mensagens de erro
    └── mocks/           # dados iniciais do módulo financeiro
```

## Execução

```bash
cd app
npm install
cp .env.example .env     # definir EXPO_PUBLIC_API_URL
npx expo start           # abrir no Expo Go
```

As variáveis `EXPO_PUBLIC_*` são substituídas em tempo de build e devem
ser lidas de forma estática (`process.env.EXPO_PUBLIC_API_URL`), como em
`src/config/env.ts`; acesso dinâmico chega indefinido no build publicado.

## Build e atualização

```bash
npx eas-cli@latest build --platform android --profile preview   # gera o .apk
npx eas-cli@latest update --channel preview                     # publica correção de JavaScript
```

Uma atualização publicada no canal `preview` é baixada em uma abertura do
aplicativo e aplicada na seguinte. Mudanças em código nativo exigem novo
build. Antes de publicar, verifique os tipos com `npx tsc --noEmit`.

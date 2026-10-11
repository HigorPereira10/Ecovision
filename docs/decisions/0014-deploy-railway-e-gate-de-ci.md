# ADR 0014: Deploy no Railway como monorepo compartilhado, com gate de CI

**Status:** Decidido e em produção (2026-10-10).
API viva em `https://ecovision-production.up.railway.app`.

## Contexto

O trial gratuito do Railway venceu, e o projeto precisava de um endereço
fixo: enquanto a API rodava na máquina de desenvolvimento, o app
dependia do IP da rede local, o que inviabiliza testar o aplicativo fora
de casa e inviabiliza a demonstração na banca.

O grupo assinou o plano **Hobby** (5 dólares por mês).

## Decisão 1: nenhum root directory, e um `requirements.txt` na raiz

O caminho óbvio seria apontar o serviço do Railway para a pasta
`cloud/`. **Não funciona**, e o modo de falhar é silencioso.

Quando o Railway recebe um root directory, ele baixa **somente** os
arquivos daquela pasta, e diretórios irmãos ficam de fora. O modelo de
IA vive em `ml/models/` (irmão de `cloud/`), então ele desapareceria do
container e a API responderia `"indisponivel"` em toda captura, **sem
erro visível**: a inferência degrada em vez de falhar
([ADR 0011](0011-escopo-de-tres-classes.md)).

O próprio Railway chama esse caso de "shared monorepo" e recomenda não
definir root directory, usando um start command que entra na pasta certa.
Daí as três peças:

| Arquivo | Função |
|---|---|
| `requirements.txt` na raiz | Nixpacks decide a linguagem olhando a raiz do repositório. Sem ele, não reconhece o projeto como Python e o build falha. Contém só `-r cloud/requirements.txt` |
| `.python-version` | Fixa 3.11, a mesma versão que a CI usa. Testar numa versão diferente da que roda em produção esconde incompatibilidade de dependência |
| `railway.json` | `startCommand` entra em `cloud/`, aplica as migrations e sobe o Uvicorn com **1 worker** |

## Decisão 2: as migrations rodam no start command

`cd cloud && alembic upgrade head && uvicorn ...`

O `&&` é o ponto: se a migration falhar, o Uvicorn **não sobe**. Isso é
melhor do que subir uma API cujo código espera colunas que o banco não
tem, porque esse segundo caso só aparece quando um produtor usa a tela
errada.

## Decisão 3: 1 único worker

Herdado do Blueprint v3.0 e mantido. O interpretador TFLite é carregado
em memória no startup, e cada worker carregaria a própria cópia. Com a
RAM do Hobby, mais de um worker é o caminho mais curto para o processo
morrer sob a primeira captura.

É também a premissa do [ADR 0008](0008-deteccao-dispositivo-inativo.md)
(sem job em background) e do [ADR 0012](0012-notificacao-local-sem-push.md)
(sem push de servidor). As três decisões são a mesma decisão vista de
ângulos diferentes.

## Decisão 4: "Wait for CI" ligado, e CI sem filtro de caminho

O Railway publica a cada push na `main`. Com o **Wait for CI** ligado,
ele espera os checks do GitHub passarem antes de subir, então código com
teste quebrado não chega a produção.

Isso forçou uma mudança na CI: o workflow tinha filtro por pasta, para
não disparar em commit de documentação pura. **Com filtro, um push que
mexesse só em `docs/` não geraria check nenhum, e o deploy ficaria
esperando por um resultado que nunca chegaria.** O filtro foi removido.

O custo é rodar cerca de um minuto de CI em commit de documentação. O
benefício é que todo commit que chega na `main` tem um veredito, que é
justamente o que torna o Wait for CI confiável.

Verificado na prática: o build começou 46 segundos depois de os checks
ficarem verdes, e um push com CI em andamento não iniciou build nenhum.

## Decisão 5: o app recebe atualização por EAS Update, não por APK novo

O APK instalado no Android aponta para o canal `preview` do EAS Update.
Correção de JavaScript ou de tela chega sem reinstalar nada: o app baixa
a atualização numa abertura e aplica na seguinte.

Isso **não** vale para mudança que toque código nativo (dependência nova
com parte nativa, permissão nova, alteração em `app.json` que afete o
build). Nesses casos é build novo, obrigatoriamente.

## Limitações assumidas do plano Hobby

| Limitação | Efeito | Como foi contornada |
|---|---|---|
| Portas de e-mail (25, 465, 587, 2525) bloqueadas | SMTP nunca funciona de dentro do Railway | API HTTP do Brevo na porta 443, [ADR 0013](0013-email-transacional-brevo.md) |
| RAM limitada | Não cabe `tensorflow` completo | Só `tflite-runtime` ou `ai-edge-litert`, regra do Blueprint Seção 4.4 |
| Sem volume persistente | Nada pode ser gravado em disco | Imagem vai para o Supabase Storage, processamento em `BytesIO`, log em `stdout` |

## iOS

Nenhum build de iOS existe, porque ainda não testamos.

## Implementação

- `railway.json`, `requirements.txt` (raiz), `.python-version`
- `.github/workflows/tests.yml`
- `app/eas.json` (canais do EAS Update)

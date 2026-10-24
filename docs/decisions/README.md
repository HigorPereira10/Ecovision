# docs/decisions: Architecture Decision Records (ADRs)

Um arquivo por decisão relevante, incluindo o motivo e (quando
aplicável) o que foi descartado. Convenção de nome:
`NNNN-titulo-curto-em-kebab-case.md`.

Para que serve: permitir defender cada escolha na banca sem depender da
memória do grupo, e deixar rastro de quando uma decisão deixou de valer.
Uma decisão superada **não é apagada**: ela recebe nota de status
apontando para a que a substituiu. O ADR 0003 é o exemplo, e o porquê
de ele ter caducado é em si um bom argumento de banca.

## Hardware e plataforma

- [0001: Camera Module 3 (não V2)](0001-camera-module-3.md)
- [0004: Raspberry Pi 3 Model B+ no lugar do Pi Zero 2 W](0004-raspberry-pi-3b-plus.md)
- [0002: Framework de frontend: Expo (React Native)](0002-frontend-framework-pendente.md)
- [0014: Deploy no Railway como monorepo compartilhado, com gate de CI](0014-deploy-railway-e-gate-de-ci.md)
- [0015: Leitura do ADS1115 por smbus2, fora da pilha Adafruit](0015-ads1115-por-smbus2.md)

## Segurança e acesso

- [0003: Autenticação dual (credencial de dispositivo + JWT/bcrypt)](0003-autenticacao-dual.md)
  — parte do dispositivo **superada pelo 0009**
- [0009: Credencial por dispositivo e pareamento por código](0009-credencial-por-dispositivo.md)
- [0010: Cadastro aberto, RBAC por posse de dispositivo e confirmação por e-mail](0010-cadastro-aberto-e-rbac.md)
- [0013: E-mail transacional pela API HTTP do Brevo](0013-email-transacional-brevo.md)

## Regras agronômicas e de IA

- [0005: Limiares de risco ambiental (temperatura, umidade do ar, umidade do solo)](0005-limiares-ambientais.md)
- [0006: Recomendações de manejo por classe de diagnóstico](0006-recomendacoes-por-diagnostico.md)
- [0011: Escopo do modelo reduzido a três classes](0011-escopo-de-tres-classes.md)
  — inclui o ajuste de dois domínios que está em produção
- [0016: Foto ruim não vira diagnóstico](0016-guarda-de-qualidade-de-imagem.md)

## Comportamento do sistema

- [0007: Divisão final de tarefas da equipe](0007-divisao-equipe-final.md)
- [0008: Detecção de dispositivo IoT inativo (falha silenciosa)](0008-deteccao-dispositivo-inativo.md)
- [0012: Notificação local em vez de push de servidor](0012-notificacao-local-sem-push.md)

---

Ao tomar novas decisões de arquitetura durante o desenvolvimento,
adicionar um novo ADR aqui em vez de só decidir em chat ou reunião.

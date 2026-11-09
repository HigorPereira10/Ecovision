# cloud/tests

Testes automatizados da API (210 testes). Rodam sem Supabase e sem envio
de e-mail: o banco é um SQLite em memória, o Storage é simulado e as
variáveis de e-mail são esvaziadas em `conftest.py`.

| Arquivo | Testes | O que verifica |
|---|---|---|
| `test_diagnostico.py` | 17 | Fluxo completo de `POST /diagnostico`: autenticação, gravação, leituras ausentes, idempotência e alertas |
| `test_leituras.py` | 7 | `POST /leituras`, leituras de 15 minutos sem foto |
| `test_janelas.py` | 20 | Recorte em janelas, filtro por cobertura verde e regra de decisão |
| `test_inference.py` | 12 | Carregamento do modelo, pré-processamento e verificação de qualidade da imagem |
| `test_pressao_infecciosa.py` | 49 | Contexto ambiental do diagnóstico |
| `test_alertas_ambientais.py` | 9 | Limiares de temperatura e umidade |
| `test_alertas_dispositivo.py` | 7 | Detecção de dispositivo atrasado ou inativo |
| `test_alertas.py` | 7 | Listagem e marcação de alertas |
| `test_escopo.py` | 7 | Filtro por dono em todas as consultas |
| `test_cadastro_e_pareamento.py` | 17 | Cadastro e vínculo de dispositivo por código |
| `test_email_verificacao.py` | 17 | Confirmação de conta, reenvio de código e recuperação de senha |
| `test_security.py` | 11 | Hash de senha, tokens e credencial de dispositivo |
| `test_auth.py` | 6 | Login e renovação de sessão |
| `test_historico.py` | 9 | Histórico de diagnósticos e leituras |
| `test_dispositivos.py`, `test_usuarios.py`, `test_health.py`, `test_cors.py` | 15 | Demais rotas e configuração |

`fixtures/captura_dispositivo.jpg` é uma captura real do dispositivo,
reduzida, usada para verificar que fotos válidas passam pela verificação
de qualidade.

## Execução

```bash
cd cloud
pip install -r requirements.txt -r tests/requirements-test.txt
pytest -q
```

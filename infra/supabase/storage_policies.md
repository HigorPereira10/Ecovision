# Supabase Storage

- **Bucket:** `ecovision-imagens`, privado.
- **Caminho dos arquivos:** `{device_id}/{timestamp}.jpg`.
- **Escrita:** somente a API, com a chave de serviço
  (`SUPABASE_SERVICE_ROLE_KEY`). O aplicativo nunca acessa o Supabase
  diretamente.
- **Leitura:** a API gera URLs assinadas com validade de 1 hora, em lote,
  na rota `GET /diagnosticos` (`cloud/app/storage/supabase_storage.py`).
  O caminho previsível dos arquivos e o caráter privado das imagens da
  estufa tornam um bucket público inadequado.
- **Falhas:** se a URL de uma imagem não puder ser gerada, aquele item
  volta sem URL, sem derrubar a lista inteira.
- O banco guarda apenas o caminho no bucket
  (`registros_imagem.caminho_arquivo`), não a URL, que expira.

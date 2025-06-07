# Funcionamento do "Monitor de lives do Youtube"

**Este não é o projeto final do TCC**, é apenas um side project para apoiar na coleta de mensagens de chats ao vivo do Youtube.

### Resumo

- O monitor detecta novas lives e inicia automaticamente a coleta de chats, metadados e logs do processo.
- Cada transmissão monitorada gera dois arquivos principais: um com metadados da live e outro com as mensagens do chat.
- Logs diários registram o consumo de quota e o funcionamento do sistema.

### Principais características

- **Rotação automática de chaves:**  
  Quando a quota (10 000 u/dia) de uma chave estoura, o sistema troca para a próxima sem interromper a coleta.

- **Intervalo dinâmico:**  
  - 22 h – 00 h → varredura a cada **10 min** (`INTERVALO_CURTO`)
  - Demais horários → a cada **60 min** (`INTERVALO_LONGO`)

- **Painel Rich no terminal:**  
  Mostra lista de lives ativas, título e duração de cada live.

- **Travas** (`trava_<VIDEOID>`):  
  Impedem que a mesma live seja capturada por processos duplicados.

- **Logs de quota:**  
  Cada linha do arquivo `log_consumo_YYYYMMDD.txt` registra quantas chamadas `search.list` (100 u) e `videos.list` (1 u) foram feitas no ciclo.

### Visão geral dos arquivos

- **monitorar_lives.py**: Varre os canais, detecta novas transmissões ao vivo, grava metadados e dispara o coletor de chat.
- **capturar_chat.py**: Recebe o `videoId` e grava o replay do chat em CSV durante a live.
- **yt_api_manager.py**: Singleton que faz as chamadas à YouTube API e alterna as chaves automaticamente quando a quota estoura.
- **yt_api_config.py**: Lista de chaves `youtube_keys` e parâmetros de timeout.
- **canais.txt**: Um ID (ou URL) de canal por linha.

### Fluxo
```
canais.txt
|
monitorar_lives.py → detecta live ativa
| |
|------------------------> coleta metadados e salva em dados/metadados/metadados_VIDEOID.json
| |
| |
|---------> chama capturar_chat.py -----> gera dados/chats/<canal>__<data>__<hora>__VIDEOID/chat.csv
|
scripts/yt_api_config.py (chaves da API)
|
log_consumo_YYYYMMDD.txt (logs diários de consumo)
```

### Como executar

1. Instale dependências do projeto: `pip install -r requisitos.txt`

2. Configure suas chaves de API: 
    - Renomeie o arquivo `yt_api_config_example` para `yt_api_config`
    - Preencha o campo `youtube_keys` com suas chaves API do Youtube
3. Adicione os IDs (ou URLs) dos canais no arquivo `canais.txt` (um por linha).

4. Inicie o monitor executando o arquivo `monitorar_lives.py`

### Trabalhos futuros (ideias)

- Dashboard web em Flask exibindo painéis de lives e consumo em tempo-real.
- Trocar `search.list` (100 u) por **playlistItems + videos** (2 u) para reduzir ainda mais a quota.

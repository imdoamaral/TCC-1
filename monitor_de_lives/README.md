# Monitor de Lives do YouTube

**Este não é o projeto final do TCC.**  
É um *side project* de apoio à coleta automatizada de mensagens em chats de transmissões ao vivo no YouTube.

## 📌 Resumo

- Detecta novas lives automaticamente.
- Inicia a coleta do **chat ao vivo** e **metadados da transmissão**.
- Registra logs diários de consumo de quota e eventos do sistema.

## ✨ Principais características

- **Rotação automática de chaves**  
  Ao atingir o limite de uso da API (10.000 unidades/dia), o sistema troca para a próxima chave sem interrupções.

- **Intervalo de varredura adaptativo**  
  - Das 21h às 00h → a cada **10 minutos** (`INTERVALO_CURTO`)  
  - Demais horários → a cada **60 minutos** (`INTERVALO_LONGO`)

- **Painel visual no terminal (Rich)**  
  Mostra lives ativas, título e tempo de duração.

- **Travas de concorrência** (`trava_<VIDEOID>`)  
  Garantem que transmissões não sejam processadas mais de uma vez simultaneamente.

- **Logs de quota da API**  
  Exemplo de entrada em `log_consumo_YYYYMMDD.txt`:  
  > `search.list` (100 u), `videos.list` (1 u), etc.

---

## 📁 Visão geral dos arquivos

| Arquivo                         | Função                                                                 |
|--------------------------------|------------------------------------------------------------------------|
| `monitorar_lives.py`           | Varre os canais, detecta novas lives, salva metadados e chama o coletor de chat |
| `capturar_chat.py`             | Recebe um `videoId` e grava o replay do chat em CSV durante a transmissão |
| `youtube_api_singleton.py`     | Singleton que gerencia a API e troca de chave automaticamente em caso de quota |
| `youtube_api_config.py`        | Contém lista `youtube_keys` e parâmetros como `try_again_timeout`     |
| `canais.txt`                   | Um ID ou URL de canal por linha                                       |

---

## 🔄 Fluxo geral

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
scripts/youtube_api_config.py (chaves da API)
|
log_consumo_YYYYMMDD.txt (logs diários de consumo)
```

### ✅ Como executar

1. **Instale as dependências do projeto:**
   ```bash
   pip install -r requisitos.txt
   ```

2. **Configure suas chaves de API:**
   - Renomeie o arquivo `youtube_api_config_exemplo.py` para `youtube_api_config.py`
   - Preencha o campo `youtube_keys` com suas chaves da YouTube Data API

3. **Adicione os IDs (ou URLs) dos canais no arquivo `canais.txt`:**  
   Um canal por linha.

4. **Inicie o monitor executando:**
   ```bash
   python scripts/monitorar_lives.py
   ```

### 💡 Trabalhos futuros (ideias)

- Criar um dashboard web com Flask para exibir painéis de lives ativas e consumo de quota em tempo real.
- Substituir chamadas `search.list` (100 u) por combinação de `playlistItems + videos.list` (2 u), otimizando o uso da quota da API.


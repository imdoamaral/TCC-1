# Funcionamento do "Monitor de lives do Youtube"

**Este não é o projeto final do TCC**, é apenas um side project para apoiar na coleta de mensagens de chats ao vivo do Youtube.

### Resumo

- O monitor detecta novas lives e inicia automaticamente a coleta de chats, metadados e logs do processo.
- Cada transmissão monitorada gera dois arquivos principais: um com metadados da live e outro com as mensagens do chat.
- Logs diários registram o consumo de quota e o funcionamento do sistema.


### Fluxo
```
canais.txt
|
monitorar_lives.py ---> detecta live ativa
| |
|--------------------------> coleta metadados e salva em metadados/metadados_VIDEOID.json
| |
| |
|---------> chama captura_chat.py ------------> gera chats/chat_VIDEOID.csv
|
.env (chave)
|
log_consumo_YYYYMMDD.txt (logs diários de consumo)
```
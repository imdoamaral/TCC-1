from googleapiclient.discovery import build
import pandas as pd
import time
import os
import re
import csv
from dotenv import load_dotenv
from datetime import datetime
import sys

# Carregamento de variáveis e configurações globais
load_dotenv()
CHAVE_API = os.getenv('YOUTUBE_API_KEY')

INTERVALO_COLETA = 30  # Tempo (em segundos) entre cada busca de mensagens do chat.

youtube = build('youtube', 'v3', developerKey=CHAVE_API)

# Funções utilitárias
def gerar_nome_pasta(texto):
    import unicodedata
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', texto)
    return texto

def extrair_data_hora_iso(iso_str):
    if not iso_str:
        return '', ''
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        data_fmt = dt.strftime('%Y-%m-%d')
        hora_fmt = dt.strftime('%H-%M-%S')
        return data_fmt, hora_fmt
    except Exception:
        return iso_str[:10], iso_str[11:19].replace(':', '-')

def remover_arquivo_de_trava(id_video):
    caminho_trava = f'dados/chats/trava_{id_video}'
    if os.path.exists(caminho_trava):
        try:
            os.remove(caminho_trava)
            print(f"Arquivo de trava {caminho_trava} removido com sucesso.")
        except Exception as e:
            print(f"Erro ao remover arquivo de trava: {e}")

def obter_id_chat_e_metadados(id_video):
    requisicao = youtube.videos().list(
        part='snippet,liveStreamingDetails',
        id=id_video
    )
    resposta = requisicao.execute()
    itens = resposta.get('items', [])
    if not itens:
        print('Vídeo não encontrado ou não está ao vivo.')
        return None, None
    item = itens[0]
    detalhes_live = item.get('liveStreamingDetails', {})
    id_chat = detalhes_live.get('activeLiveChatId') or detalhes_live.get('liveChatId')
    if not id_chat:
        print('Esta live não possui chat ativo ou não está ao vivo.')
        return None, None

    metadados = {
        'id_video': id_video,
        'titulo': item['snippet'].get('title', ''),
        'descricao': item['snippet'].get('description', ''),
        'canal': item['snippet'].get('channelTitle', ''),
        'data_publicacao': item['snippet'].get('publishedAt', ''),
        'data_inicio_live': detalhes_live.get('actualStartTime', ''),
        'espectadores_atuais': detalhes_live.get('concurrentViewers', '')
    }
    return id_chat, metadados

# Processamento principal

# 1. Captura o ID do vídeo da linha de comando ou usa um valor padrão para testes
if len(sys.argv) > 1:
    id_video = sys.argv[1]
else:
    id_video = 'P5nPF1gbl4Q'  # Valor padrão para testes. Substitua pelo desejado.

# 2. Busca metadados da live e valida existência do chat ao vivo
id_chat, metadados = obter_id_chat_e_metadados(id_video)
if not id_chat:
    exit()

data_fmt, hora_fmt = extrair_data_hora_iso(metadados['data_inicio_live'])
nome_canal = gerar_nome_pasta(metadados['canal'])
pasta_live = os.path.join('dados', f"{nome_canal}__{data_fmt}__{hora_fmt}__{id_video}")
os.makedirs(pasta_live, exist_ok=True)
arquivo_csv = os.path.join(pasta_live, 'chat.csv')
arquivo_metadados = os.path.join(pasta_live, 'metadados.csv')

print(f"Iniciando captura do chat da live: '{metadados['titulo']}' (ID: {id_video}) do canal '{metadados['canal']}'.")

# 3. Salva os metadados em arquivo CSV para referência futura.
with open(arquivo_metadados, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=metadados.keys())
    writer.writeheader()
    writer.writerow(metadados)

# 4. Loop principal de coleta das mensagens do chat ao vivo
mensagens = []
proximo_token = None
contador_sem_mensagem = 0

try:
    while True:
        # Consulta a API do YouTube para obter até 200 mensagens novas do chat
        requisicao = youtube.liveChatMessages().list(
            liveChatId=id_chat,
            part='snippet,authorDetails',
            maxResults=200,
            pageToken=proximo_token
        )
        resposta = requisicao.execute()
        for item in resposta['items']:
            mensagem = item['snippet'].get('displayMessage')
            if not mensagem:
                contador_sem_mensagem += 1
                continue
            mensagens.append({
                'id_video': id_video,
                'timestamp': item['snippet']['publishedAt'],
                'autor': item['authorDetails']['displayName'],
                'mensagem': mensagem
            })
        # Salva as mensagens já coletadas no arquivo CSV
        if mensagens:
            pd.DataFrame(mensagens).to_csv(arquivo_csv, index=False, encoding='utf-8')
            print(f"Total de mensagens coletadas até agora: {len(mensagens)}")
        if contador_sem_mensagem > 0:
            print(f"Mensagens sem texto ignoradas nesta rodada: {contador_sem_mensagem}")
            contador_sem_mensagem = 0
        # Avança para o próximo lote de mensagens, se houver
        proximo_token = resposta.get('nextPageToken')
        time.sleep(INTERVALO_COLETA)
except KeyboardInterrupt:
    print("Coleta interrompida pelo usuário.")
except Exception as e:
    print(f"Ocorreu um erro durante a coleta: {e}")
finally:
    remover_arquivo_de_trava(metadados['id_video'])

if mensagens:
    pd.DataFrame(mensagens).to_csv(arquivo_csv, index=False, encoding='utf-8')
    print(f"Mensagens finais exportadas para {arquivo_csv}")
else:
    print("Nenhuma mensagem foi coletada do chat.")


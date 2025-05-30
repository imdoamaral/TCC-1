"""
Script para captura de mensagens do chat de uma live do YouTube,
organizando cada live em uma subpasta por canal, data e hora de início.
Compatível com execução manual ou chamada automática pelo monitor.
"""

from googleapiclient.discovery import build
import pandas as pd
import time
import os
import re
import csv
from dotenv import load_dotenv
from datetime import datetime
import sys

# Carrega variável .env
load_dotenv()
CHAVE_API = os.getenv('YOUTUBE_API_KEY')

intervalo_coleta = 30  # segundos

youtube = build('youtube', 'v3', developerKey=CHAVE_API)

def slugify(texto):
    """Remove acentos, espaços e caracteres problemáticos para nome de pasta"""
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

def remover_lockfile(id_video):
    lockfile = f'dados/chats/lock_{id_video}'
    if os.path.exists(lockfile):
        try:
            os.remove(lockfile)
            print(f"Lockfile {lockfile} removido com sucesso.")
        except Exception as e:
            print(f"Erro ao remover lockfile: {e}")

def obter_chat_id_e_metadados(id_video):
    request = youtube.videos().list(
        part='snippet,liveStreamingDetails',
        id=id_video
    )
    response = request.execute()
    itens = response.get('items', [])
    if not itens:
        print('Vídeo não encontrado ou não está ao vivo.')
        return None, None
    item = itens[0]
    detalhes_live = item.get('liveStreamingDetails', {})
    chat_id = detalhes_live.get('activeLiveChatId') or detalhes_live.get('liveChatId')
    if not chat_id:
        print('Live não possui chat ativo ou não está ao vivo.')
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
    return chat_id, metadados

# Permite passar o ID da live por argumento de linha de comando
if len(sys.argv) > 1:
    id_video = sys.argv[1]
else:
    id_video = 'P5nPF1gbl4Q'  # Substitua por padrão desejado para testes manuais

chat_id, metadados = obter_chat_id_e_metadados(id_video)
if not chat_id:
    exit()

data_fmt, hora_fmt = extrair_data_hora_iso(metadados['data_inicio_live'])
nome_canal = slugify(metadados['canal'])
pasta_live = os.path.join('dados', f"{nome_canal}__{data_fmt}__{hora_fmt}__{id_video}")
os.makedirs(pasta_live, exist_ok=True)
arquivo_csv = os.path.join(pasta_live, 'chat.csv')
arquivo_metadados = os.path.join(pasta_live, 'metadados.csv')

print(f"Capturando chat da live: {metadados['titulo']} ({id_video}) do canal {metadados['canal']}")

# Salva metadados em arquivo CSV (1 linha, cabeçalho)
with open(arquivo_metadados, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=metadados.keys())
    writer.writeheader()
    writer.writerow(metadados)

mensagens = []
proximo_token = None
contador_sem_mensagem = 0

try:
    while True:
        req = youtube.liveChatMessages().list(
            liveChatId=chat_id,
            part='snippet,authorDetails',
            maxResults=200,
            pageToken=proximo_token
        )
        resp = req.execute()
        for item in resp['items']:
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
        if mensagens:
            pd.DataFrame(mensagens).to_csv(arquivo_csv, index=False, encoding='utf-8')
            print(f"Mensagens coletadas até agora: {len(mensagens)}")
        if contador_sem_mensagem > 0:
            print(f"Mensagens sem texto ignoradas nesta rodada: {contador_sem_mensagem}")
            contador_sem_mensagem = 0
        proximo_token = resp.get('nextPageToken')
        time.sleep(intervalo_coleta)
except KeyboardInterrupt:
    print("Coleta interrompida pelo usuário.")
except Exception as e:
    print(f"Erro: {e}")
finally:
    remover_lockfile(metadados['id_video'])

if mensagens:
    pd.DataFrame(mensagens).to_csv(arquivo_csv, index=False, encoding='utf-8')
    print(f"Mensagens finais exportadas para {arquivo_csv}")
else:
    print("Nenhuma mensagem coletada.")

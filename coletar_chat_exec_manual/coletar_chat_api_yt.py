from googleapiclient.discovery import build
import pandas as pd
import time
import os
from dotenv import load_dotenv

# Carrega variável do .env
load_dotenv()
CHAVE_API = os.getenv('YOUTUBE_API_KEY')

# ID da live a ser coletada
id_video = 'ID_DA_LIVE'
intervalo_coleta = 30  # segundos

# Pasta de saída
pasta_saida = 'dados/chats'
os.makedirs(pasta_saida, exist_ok=True)
arquivo_csv = os.path.join(pasta_saida, f'chat_{id_video}.csv')
arquivo_metadados = os.path.join(pasta_saida, f'metadados_{id_video}.txt')

youtube = build('youtube', 'v3', developerKey=CHAVE_API)

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
        'canal': item['snippet'].get('channelTitle', ''),
        'data_inicio': detalhes_live.get('actualStartTime', ''),
    }
    return chat_id, metadados

chat_id, metadados = obter_chat_id_e_metadados(id_video)
if not chat_id:
    exit()

print(f"Capturando chat da live: {metadados['titulo']} ({id_video})")

# Salva metadados em arquivo txt
with open(arquivo_metadados, 'w', encoding='utf-8') as f:
    for chave, valor in metadados.items():
        f.write(f"{chave}: {valor}\n")

mensagens = []
proximo_token = None

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
            mensagens.append({
                'id_video': id_video,
                'timestamp': item['snippet']['publishedAt'],
                'autor': item['authorDetails']['displayName'],
                'mensagem': item['snippet']['displayMessage']
            })
        if mensagens:
            pd.DataFrame(mensagens).to_csv(arquivo_csv, index=False, encoding='utf-8')
            print(f"Mensagens coletadas até agora: {len(mensagens)}")
        proximo_token = resp.get('nextPageToken')
        time.sleep(intervalo_coleta)
except KeyboardInterrupt:
    print("Coleta interrompida pelo usuário.")
except Exception as e:
    print(f"Erro: {e}")

if mensagens:
    pd.DataFrame(mensagens).to_csv(arquivo_csv, index=False, encoding='utf-8')
    print(f"Mensagens finais exportadas para {arquivo_csv}")
else:
    print("Nenhuma mensagem coletada.")

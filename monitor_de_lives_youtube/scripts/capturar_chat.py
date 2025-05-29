from googleapiclient.discovery import build
import pandas as pd
import time
import os
from dotenv import load_dotenv

# Carrega variável .env
API_KEY = os.getenv('YOUTUBE_API_KEY')

# ID da live a ser coletada
VIDEO_ID = 'ID_DA_LIVE'
POLLING_INTERVAL = 30  # segundos

# Pasta de saída
OUTPUT_DIR = 'dados/chats'
os.makedirs(OUTPUT_DIR, exist_ok=True)
CSV_FILE = os.path.join(OUTPUT_DIR, f'chat_{VIDEO_ID}.csv')
METADADOS_FILE = os.path.join(OUTPUT_DIR, f'metadados_{VIDEO_ID}.txt')

youtube = build('youtube', 'v3', developerKey=API_KEY)

def get_live_chat_id_and_metadata(video_id):
    request = youtube.videos().list(
        part='snippet,liveStreamingDetails',
        id=video_id
    )
    response = request.execute()
    items = response.get('items', [])
    if not items:
        print('Vídeo não encontrado ou não está ao vivo.')
        return None, None
    item = items[0]
    live_details = item.get('liveStreamingDetails', {})
    live_chat_id = live_details.get('activeLiveChatId') or live_details.get('liveChatId')
    if not live_chat_id:
        print('Live não possui chat ativo ou não está ao vivo.')
        return None, None
    meta = {
        'video_id': video_id,
        'titulo': item['snippet'].get('title', ''),
        'canal': item['snippet'].get('channelTitle', ''),
        'data_inicio': live_details.get('actualStartTime', ''),
    }
    return live_chat_id, meta

live_chat_id, meta = get_live_chat_id_and_metadata(VIDEO_ID)
if not live_chat_id:
    exit()

print(f"Capturando chat da live: {meta['titulo']} ({VIDEO_ID})")

# Salva metadados em arquivo txt
with open(METADADOS_FILE, 'w', encoding='utf-8') as f:
    for k, v in meta.items():
        f.write(f"{k}: {v}\n")

messages = []
next_page_token = None

try:
    while True:
        req = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part='snippet,authorDetails',
            maxResults=200,
            pageToken=next_page_token
        )
        resp = req.execute()
        for item in resp['items']:
            messages.append({
                'video_id': VIDEO_ID,
                'timestamp': item['snippet']['publishedAt'],
                'author': item['authorDetails']['displayName'],
                'message': item['snippet']['displayMessage']
            })
        if messages:
            pd.DataFrame(messages).to_csv(CSV_FILE, index=False, encoding='utf-8')
            print(f"Mensagens coletadas até agora: {len(messages)}")
        next_page_token = resp.get('nextPageToken')
        time.sleep(POLLING_INTERVAL)
except KeyboardInterrupt:
    print("Coleta interrompida pelo usuário.")
except Exception as e:
    print(f"Erro: {e}")

if messages:
    pd.DataFrame(messages).to_csv(CSV_FILE, index=False, encoding='utf-8')
    print(f"Mensagens finais exportadas para {CSV_FILE}")
else:
    print("Nenhuma mensagem coletada.")

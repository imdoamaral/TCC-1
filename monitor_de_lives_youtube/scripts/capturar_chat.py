from googleapiclient.discovery import build
import pandas as pd
import time
import os
from dotenv import load_dotenv

# Carrega variável .env
load_dotenv()
CHAVE_API = os.getenv('YOUTUBE_API_KEY')

# ID da live a ser coletada
ID_LIVE = 'ID_DA_LIVE'
INTERVALO_COLETA = 30  # segundos

# Pasta de saída
PASTA_SAIDA = 'dados/chats'
os.makedirs(PASTA_SAIDA, exist_ok=True)
ARQUIVO_CSV = os.path.join(PASTA_SAIDA, f'chat_{ID_LIVE}.csv')
ARQUIVO_METADADOS = os.path.join(PASTA_SAIDA, f'metadados_{ID_LIVE}.txt')

youtube = build('youtube', 'v3', developerKey=CHAVE_API)

def obter_chat_id_e_metadados(id_live):
    request = youtube.videos().list(
        part='snippet,liveStreamingDetails',
        id=id_live
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
        'id_live': id_live,
        'titulo': item['snippet'].get('title', ''),
        'canal': item['snippet'].get('channelTitle', ''),
        'data_inicio': detalhes_live.get('actualStartTime', ''),
    }
    return chat_id, metadados

chat_id, metadados = obter_chat_id_e_metadados(ID_LIVE)
if not chat_id:
    exit()

print(f"Capturando chat da live: {metadados['titulo']} ({ID_LIVE})")

# Salva metadados em arquivo txt
with open(ARQUIVO_METADADOS, 'w', encoding='utf-8') as f:
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
                'id_live': ID_LIVE,
                'timestamp': item['snippet']['publishedAt'],
                'autor': item['authorDetails']['displayName'],
                'mensagem': item['snippet']['displayMessage']
            })
        if mensagens:
            pd.DataFrame(mensagens).to_csv(ARQUIVO_CSV, index=False, encoding='utf-8')
            print(f"Mensagens coletadas até agora: {len(mensagens)}")
        proximo_token = resp.get('nextPageToken')
        time.sleep(INTERVALO_COLETA)
except KeyboardInterrupt:
    print("Coleta interrompida pelo usuário.")
except Exception as e:
    print(f"Erro: {e}")

if mensagens:
    pd.DataFrame(mensagens).to_csv(ARQUIVO_CSV, index=False, encoding='utf-8')
    print(f"Mensagens finais exportadas para {ARQUIVO_CSV}")
else:
    print("Nenhuma mensagem coletada.")

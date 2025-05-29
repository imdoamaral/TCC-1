import time
import subprocess
import os
import json
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')

# Horários para intervalo dinâmico
INTERVALO_CURTO = 600   # 10 min
INTERVALO_LONGO = 3600  # 1 hora

def obter_check_interval():
    """Define o intervalo conforme o horário."""
    agora = datetime.now()
    hora = agora.hour
    # Das 21h às 0h (inclusive)
    if hora >= 21 or hora <= 0:
        return INTERVALO_CURTO
    else:
        return INTERVALO_LONGO

def logar_consumo(qtd_search=0, qtd_metadados=0):
    """Salva o log de consumo em arquivo por dia."""
    hoje = datetime.now().strftime('%Y%m%d')
    caminho_log = f'log_consumo_{hoje}.txt'
    total = qtd_search*100 + qtd_metadados*1
    log_str = f"{datetime.now().isoformat()} - SEARCH_LIST: {qtd_search}, VIDEOS_LIST: {qtd_metadados}, TOTAL: {total} pontos\n"
    with open(caminho_log, 'a', encoding='utf-8') as f:
        f.write(log_str)

def criar_pastas():
    os.makedirs('dados/chats', exist_ok=True)
    os.makedirs('dados/metadados', exist_ok=True)

def carregar_canais():
    with open('TCC_1/youtube_live_monitor/canais.txt', 'r') as f:
        canais = [linha.strip() for linha in f if linha.strip()]
    return canais

def buscar_lives_ativas(youtube, channel_id):
    request = youtube.search().list(
        part='id,snippet',
        channelId=channel_id,
        eventType='live',
        type='video',
        maxResults=1
    )
    response = request.execute()
    lives = []
    for item in response.get('items', []):
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        lives.append((video_id, title))
    return lives

def buscar_metadados(youtube, video_id):
    request = youtube.videos().list(
        part='snippet,liveStreamingDetails',
        id=video_id
    )
    response = request.execute()
    items = response.get('items', [])
    if not items:
        return {}
    item = items[0]
    metadados = {
        'video_id': video_id,
        'titulo': item['snippet'].get('title', ''),
        'descricao': item['snippet'].get('description', ''),
        'canal': item['snippet'].get('channelTitle', ''),
        'data_publicacao': item['snippet'].get('publishedAt', ''),
        'data_inicio_live': item.get('liveStreamingDetails', {}).get('actualStartTime', ''),
        'concurrentViewers': item.get('liveStreamingDetails', {}).get('concurrentViewers', ''),
    }
    return metadados

def ja_esta_capturando(video_id):
    return os.path.exists(f'dados/chats/chat_{video_id}.csv')

def salvar_metadados(video_id, metadados):
    with open(f'dados/metadados/metadados_{video_id}.json', 'w', encoding='utf-8') as f:
        json.dump(metadados, f, ensure_ascii=False, indent=2)

def iniciar_captura(video_id):
    print(f"Iniciando captura do chat da live {video_id}...")
    subprocess.Popen([
        'python', os.path.join('scripts', 'capturar_chat.py'), video_id
    ])

def arquivo_chat_foi_atualizado(video_id, minutos=15):
    caminho = f'dados/chats/chat_{video_id}.csv'
    if not os.path.exists(caminho):
        return False
    ultima_modificacao = os.path.getmtime(caminho)
    tempo_atual = time.time()
    return (tempo_atual - ultima_modificacao) < (minutos * 60)

def main():
    criar_pastas()
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    canais = carregar_canais()
    canais_em_live = {}  # canal_id: video_id

    print("Monitorando canais:", canais)
    while True:
        qtd_search = 0
        qtd_metadados = 0

        for canal in canais:
            # Se o canal já está em live, verifica se a coleta ainda está rodando
            if canal in canais_em_live:
                video_id = canais_em_live[canal]
                if not arquivo_chat_foi_atualizado(video_id, minutos=15):
                    print(f"A live do canal {canal} (vídeo {video_id}) parece ter terminado. Voltando a monitorar o canal.")
                    canais_em_live.pop(canal)
                else:
                    print(f"Canal {canal} ainda está com coleta ativa para a live {video_id}. Pausando busca por novas lives.")
                continue

            # Se não está em live, faz a busca normal
            lives = buscar_lives_ativas(youtube, canal)
            qtd_search += 1  # conta cada busca search.list
            for video_id, title in lives:
                if not ja_esta_capturando(video_id):
                    print(f"Nova live detectada em {canal}: {title} ({video_id})")
                    metadados = buscar_metadados(youtube, video_id)
                    qtd_metadados += 1  # conta cada busca videos.list
                    if metadados:
                        salvar_metadados(video_id, metadados)
                    else:
                        print(f"Não foi possível obter metadados para {video_id}")
                    iniciar_captura(video_id)
                    canais_em_live[canal] = video_id  # Marca canal como "em live"
                else:
                    print(f"Já capturando chat da live {video_id} ({title})")

        # Loga consumo a cada rodada
        logar_consumo(qtd_search, qtd_metadados)

        check_interval = obter_check_interval()
        print(f"Aguardando {check_interval // 60} minutos para a próxima checagem...")
        time.sleep(check_interval)

if __name__ == '__main__':
    main()

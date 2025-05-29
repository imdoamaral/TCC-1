import time
import subprocess
import os
import json
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime

# Carrega variável de ambiente do .env
load_dotenv()
CHAVE_API = os.getenv('YOUTUBE_API_KEY')

# Horários para intervalo dinâmico
INTERVALO_CURTO = 600   # 10 min
INTERVALO_LONGO = 3600  # 1 hora

def obter_intervalo():
    """Define o intervalo de checagem conforme o horário."""
    agora = datetime.now()
    hora = agora.hour
    # Das 21h às 0h (inclusive)
    if hora >= 21 or hora <= 0:
        return INTERVALO_CURTO
    else:
        return INTERVALO_LONGO

def registrar_consumo(qtd_busca=0, qtd_metadados=0):
    """Salva o log de consumo em arquivo diário."""
    hoje = datetime.now().strftime('%Y%m%d')
    caminho_log = f'log_consumo_{hoje}.txt'
    total = qtd_busca*100 + qtd_metadados*1
    log_str = f"{datetime.now().isoformat()} - BUSCA_LIVE: {qtd_busca}, BUSCA_METADADOS: {qtd_metadados}, TOTAL: {total} pontos\n"
    with open(caminho_log, 'a', encoding='utf-8') as f:
        f.write(log_str)

def criar_pastas():
    os.makedirs('dados/chats', exist_ok=True)
    os.makedirs('dados/metadados', exist_ok=True)

def carregar_canais():
    with open('TCC_1/youtube_live_monitor/canais.txt', 'r') as f:
        canais = [linha.strip() for linha in f if linha.strip()]
    return canais

def buscar_lives_ativas(youtube, id_canal):
    request = youtube.search().list(
        part='id,snippet',
        channelId=id_canal,
        eventType='live',
        type='video',
        maxResults=1
    )
    response = request.execute()
    lives = []
    for item in response.get('items', []):
        id_video = item['id']['videoId']
        titulo = item['snippet']['title']
        lives.append((id_video, titulo))
    return lives

def buscar_metadados(youtube, id_video):
    request = youtube.videos().list(
        part='snippet,liveStreamingDetails',
        id=id_video
    )
    response = request.execute()
    itens = response.get('items', [])
    if not itens:
        return {}
    item = itens[0]
    metadados = {
        'id_video': id_video,
        'titulo': item['snippet'].get('title', ''),
        'descricao': item['snippet'].get('description', ''),
        'canal': item['snippet'].get('channelTitle', ''),
        'data_publicacao': item['snippet'].get('publishedAt', ''),
        'data_inicio_live': item.get('liveStreamingDetails', {}).get('actualStartTime', ''),
        'espectadores_atuais': item.get('liveStreamingDetails', {}).get('concurrentViewers', ''),
    }
    return metadados

def ja_esta_capturando(id_video):
    return os.path.exists(f'dados/chats/chat_{id_video}.csv')

def salvar_metadados(id_video, metadados):
    with open(f'dados/metadados/metadados_{id_video}.json', 'w', encoding='utf-8') as f:
        json.dump(metadados, f, ensure_ascii=False, indent=2)

def iniciar_captura(id_video):
    print(f"Iniciando captura do chat da live {id_video}...")
    subprocess.Popen([
        'python', os.path.join('scripts', 'capturar_chat.py'), id_video
    ])

def chat_foi_atualizado(id_video, minutos=15):
    caminho = f'dados/chats/chat_{id_video}.csv'
    if not os.path.exists(caminho):
        return False
    ultima_modificacao = os.path.getmtime(caminho)
    tempo_atual = time.time()
    return (tempo_atual - ultima_modificacao) < (minutos * 60)

def main():
    criar_pastas()
    youtube = build('youtube', 'v3', developerKey=CHAVE_API)
    canais = carregar_canais()
    canais_em_live = {}  # id_canal: id_video

    print("Monitorando canais:", canais)
    while True:
        qtd_busca = 0
        qtd_metadados = 0

        for canal in canais:
            # Se o canal já está em live, verifica se a coleta ainda está rodando
            if canal in canais_em_live:
                id_video = canais_em_live[canal]
                if not chat_foi_atualizado(id_video, minutos=15):
                    print(f"A live do canal {canal} (vídeo {id_video}) parece ter terminado. Voltando a monitorar o canal.")
                    canais_em_live.pop(canal)
                else:
                    print(f"Canal {canal} ainda está com coleta ativa para a live {id_video}. Pausando busca por novas lives.")
                continue

            # Se não está em live, faz a busca normal
            lives = buscar_lives_ativas(youtube, canal)
            qtd_busca += 1  # conta cada busca de lives
            for id_video, titulo in lives:
                if not ja_esta_capturando(id_video):
                    print(f"Nova live detectada em {canal}: {titulo} ({id_video})")
                    metadados = buscar_metadados(youtube, id_video)
                    qtd_metadados += 1  # conta cada busca de metadados
                    if metadados:
                        salvar_metadados(id_video, metadados)
                    else:
                        print(f"Não foi possível obter metadados para {id_video}")
                    iniciar_captura(id_video)
                    canais_em_live[canal] = id_video  # Marca canal como "em live"
                else:
                    print(f"Já capturando chat da live {id_video} ({titulo})")

        # Registra o consumo de quota a cada rodada
        registrar_consumo(qtd_busca, qtd_metadados)

        intervalo = obter_intervalo()
        print(f"Aguardando {intervalo // 60} minutos para a próxima checagem...")
        time.sleep(intervalo)

if __name__ == '__main__':
    main()

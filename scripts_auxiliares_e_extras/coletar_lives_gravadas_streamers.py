from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime
import os
import csv
import time

# Carrega as variáveis de ambiente (.env)
load_dotenv()
CHAVE_API = os.getenv('YOUTUBE_API_KEY')

if not CHAVE_API:
    raise RuntimeError("Chave da API do YouTube não encontrada! Verifique seu arquivo .env.")

youtube = build('youtube', 'v3', developerKey=CHAVE_API)

# Dicionário: nome do canal e ID correspondente
canais = {
    # 'renanplay': 'UCP-HJIRXN-apUPSCOehEDZw',
    'luangameplay': 'UCddN6tViXZMEOfvO-rqfbNg',
    'cavalao2': 'UCSl2-bnD5irdJkk7ejJS4ow',
    'biahkov': 'UCPTmDqH4cUbTJ_XABClIFlw',
    'fabiojunior': 'UC1WdbwLH7azQtv3BAnYt_vg',
    'diegosheipado': 'UC0Zhnj_IarrejROxchWtkMQ',
    'canaldoronaldinho': 'UCjIN9CsGuLhj7NkNspZxw7g',
    'wallacegamer': 'UCb7JJAHkxdMVmFXw8tYDDdw'
}

for nome_canal, canal_id in canais.items():
    print(f'Processando canal: {nome_canal}')

    parametros_busca = {
        'channelId': canal_id,
        'part': 'id,snippet',
        'maxResults': 50,
        'order': 'date',
        'type': 'video'
    }

    ids_videos = []
    resposta_busca = youtube.search().list(**parametros_busca).execute()
    for item in resposta_busca.get('items', []):
        ids_videos.append(item['id']['videoId'])

    while 'nextPageToken' in resposta_busca:
        parametros_busca['pageToken'] = resposta_busca['nextPageToken']
        resposta_busca = youtube.search().list(**parametros_busca).execute()
        for item in resposta_busca.get('items', []):
            ids_videos.append(item['id']['videoId'])
        time.sleep(1)  # Evita rate limit

    # Agora coleta estatísticas, apenas de lives de 2025
    dados_csv = []
    cabecalho = ['Título', 'Data de publicação', 'URL', 'Visualizações', 'Duração', 'Tipo de conteúdo']

    for i in range(0, len(ids_videos), 50):
        lote_ids = ids_videos[i:i + 50]
        resposta_videos = youtube.videos().list(
            part='snippet,statistics,contentDetails,liveStreamingDetails',
            id=','.join(lote_ids)
        ).execute()

        for video in resposta_videos.get('items', []):
            snippet = video.get('snippet', {})
            data_pub = snippet.get('publishedAt', '')
            stats = video.get('statistics', {})
            detalhes = video.get('contentDetails', {})
            tipo_conteudo = snippet.get('liveBroadcastContent', '')  # pode ser 'none', 'live', 'upcoming'
            duracao = detalhes.get('duration', '')
            titulo = snippet.get('title', '')
            url = f"https://www.youtube.com/watch?v={video['id']}"
            visualizacoes = stats.get('viewCount', '0')

            # Filtrar só vídeos de 2025 e que são lives (tipo_conteudo pode ser 'none' para lives salvas)
            if data_pub:
                data = datetime.fromisoformat(data_pub.replace("Z", "+00:00"))
                if data.year == 2025:
                    dados_csv.append([titulo, data_pub, url, visualizacoes, duracao, tipo_conteudo])

        time.sleep(1)

    # Salva o CSV por canal
    nome_arquivo = f'lives_{nome_canal}_2025.csv'
    with open(nome_arquivo, 'w', newline='', encoding='utf-8') as arquivo_csv:
        escritor = csv.writer(arquivo_csv)
        escritor.writerow(cabecalho)
        escritor.writerows(dados_csv)

    print(f'Exportação concluída: {len(dados_csv)} lives de 2025 salvas em {nome_arquivo}')

print('Processamento finalizado para todos os canais.')

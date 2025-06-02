from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import csv
import time

# Carrega as variáveis do arquivo .env
load_dotenv()
# CHAVE_API = os.getenv('YOUTUBE_API_KEY')
CHAVE_API = 'AIzaSyD5boE_7iLCkIzXNIrHCBxnsz9K8MYKB2E'

if not CHAVE_API:
    raise RuntimeError("CHAVE DA API não encontrada! Verifique o arquivo .env.")

# Inicializa a API do YouTube
youtube = build('youtube', 'v3', developerKey=CHAVE_API)

# Termo de busca
termo_busca = "iceberg da calvoesfera"

# Parâmetros da busca
parametros_busca = {
    'q': termo_busca,
    'part': 'id',
    'type': 'video',
    'maxResults': 50
}

ids_videos = []
resposta_busca = youtube.search().list(**parametros_busca).execute()
for item in resposta_busca.get('items', []):
    ids_videos.append(item['id']['videoId'])

# Busca todas as páginas de resultados (caso existam mais de 50 vídeos)
while 'nextPageToken' in resposta_busca:
    parametros_busca['pageToken'] = resposta_busca['nextPageToken']
    resposta_busca = youtube.search().list(**parametros_busca).execute()
    for item in resposta_busca.get('items', []):
        ids_videos.append(item['id']['videoId'])
    # Se precisar limitar a quantidade de páginas para evitar consumo de cota, adicionar um break aqui

# Prepara a lista de dados para exportar em CSV
dados_csv = []
cabecalho = ['Título', 'Canal', 'Data de publicação', 'URL', 'Visualizações', 'Comentários']

# Para cada lote de até 50 vídeos (limite da API), busca as estatísticas e informações
for i in range(0, len(ids_videos), 50):
    lote_ids = ids_videos[i:i + 50]
    resposta_videos = youtube.videos().list(
        part='snippet,statistics',
        id=','.join(lote_ids)
    ).execute()

    for video in resposta_videos.get('items', []):
        estatisticas = video.get('statistics', {})
        snippet = video.get('snippet', {})
        titulo = snippet.get('title', '')
        canal = snippet.get('channelTitle', '')
        data_publicacao = snippet.get('publishedAt', '')
        url = f"https://www.youtube.com/watch?v={video['id']}"
        visualizacoes = estatisticas.get('viewCount', '0')
        comentarios = estatisticas.get('commentCount', '0')

        dados_csv.append([titulo, canal, data_publicacao, url, visualizacoes, comentarios])
    time.sleep(1)  # Aguarda para evitar bloqueio de requisições

# Filtro para considerar apenas vídeos com os termos desejados no título
palavras_chave = [
    'iceberg da calvoesfera',
    'iceberg da calvosfera', # cobre erros de digitação
]

dados_csv_filtrados = []
for linha in dados_csv:
    titulo = linha[0].lower()
    if any(palavra in titulo for palavra in palavras_chave):
        dados_csv_filtrados.append(linha)

# Salva apenas os vídeos filtrados em um novo arquivo CSV
with open('relatorio_video_viral_2024_filtrado.csv', 'w', newline='', encoding='utf-8') as arquivo_csv:
    escritor = csv.writer(arquivo_csv)
    escritor.writerow(cabecalho)
    escritor.writerows(dados_csv_filtrados)

print(f"Exportação concluída: {len(dados_csv_filtrados)} vídeos filtrados salvos em relatorio_video_viral_2024_filtrado.csv")
# -*- coding: utf-8 -*-
"""
Extrai **todos** os comentários (top-level + respostas) de um vídeo do YouTube
e grava em CSV.

Pré-requisitos
--------------
pip install google-api-python-client python-dotenv

Crie um arquivo .env na mesma pasta com:
YOUTUBE_API_KEY=SUAS_CHAVE_AQUI
"""

from googleapiclient.discovery import build
from dotenv import load_dotenv
from pathlib import Path
import csv
import os

# Configuração
CAMINHO_BASE = Path(__file__).resolve().parent
load_dotenv(CAMINHO_BASE / ".env") # lê .env na pasta do script

CHAVE_API   = os.getenv("YOUTUBE_API_KEY")
ID_VIDEO    = "CNCMa4MizY0" # trocar pelo ID desejado
ARQ_SAIDA   = CAMINHO_BASE / "comentarios.csv"
TAM_PAGINA  = 100 # máximo permitido pela API

# Funções
def extrair_comentarios(id_video: str, chave_api: str, arq_saida: Path) -> None:
    """Baixa comentários (inclui replies) e salva no CSV indicado."""
    youtube = build("youtube", "v3", developerKey=chave_api, cache_discovery=False)
    comentarios: list[list[str]] = []

    requisicao = youtube.commentThreads().list(
        part="snippet,replies", # inclui respostas aos proprios comentarios
        videoId=id_video,
        maxResults=TAM_PAGINA,
        textFormat="plainText"
    )

    while requisicao:
        resposta = requisicao.execute()

        for item in resposta.get("items", []):
            # ── comentário de nível superior ──
            topo = item["snippet"]["topLevelComment"]["snippet"]
            comentarios.append([
                topo["authorDisplayName"],
                topo["publishedAt"],
                topo["textDisplay"]
            ])

            # ── replies (se houver) ──
            for reply in item.get("replies", {}).get("comments", []):
                r = reply["snippet"]
                comentarios.append([
                    r["authorDisplayName"],
                    r["publishedAt"],
                    r["textDisplay"]
                ])

        requisicao = youtube.commentThreads().list_next(requisicao, resposta)

    # grava em CSV
    with arq_saida.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["autor", "data_publicacao", "comentario"])
        escritor.writerows(comentarios)

    print(f"{len(comentarios)} comentários salvos em {arq_saida}")


# Execução
if __name__ == "__main__":
    if not CHAVE_API:
        raise RuntimeError("Defina YOUTUBE_API_KEY no arquivo .env.")
    extrair_comentarios(ID_VIDEO, CHAVE_API, ARQ_SAIDA)

# -*- coding: utf-8 -*-

import os, sys, csv, re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from googleapiclient.discovery import build

#  CONFIG
ARQ_CSV = "novos_streamers_calvoesfera.csv"       # acumula vários vídeos, se necessario
CAMPOS    = ["id_video", "titulo", "descricao",
             "canal", "data_publicacao", "data_inicio_live", "espectadores_atuais"]

load_dotenv()
# API_KEY = os.getenv("YOUTUBE_API_KEY")
# if not API_KEY:
#     raise RuntimeError("Defina YOUTUBE_API_KEY no seu .env")
API_KEY = 'AIzaSyD5boE_7iLCkIzXNIrHCBxnsz9K8MYKB2E'

youtube = build("youtube", "v3", developerKey=API_KEY)

# HELPERS
def extrair_id(url: str) -> str:
    """
    Aceita formatos como:
        https://youtu.be/XXXX
        https://www.youtube.com/watch?v=XXXX
        https://www.youtube.com/watch?v=XXXX&ab_channel=YYY
    """
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    q = parse_qs(urlparse(url).query).get("v", [])
    return q[0] if q else url  # se já for só o id

def iso(dt_str):
    """Converte campo possivelmente ausente para ISO ou vazio."""
    return dt_str if dt_str else ""

# MAIN
if len(sys.argv) < 2:
    print("❌ Passe a URL do vídeo como argumento!")
    sys.exit(1)

video_id = extrair_id(sys.argv[1])
print(f"🔍 Consultando vídeo {video_id}")

resp = youtube.videos().list(
    id=video_id,
    part="snippet,liveStreamingDetails",
).execute()

if not resp["items"]:
    raise ValueError("Vídeo não encontrado ou ID inválido.")

v = resp["items"][0]
snippet = v["snippet"]
live   = v.get("liveStreamingDetails", {})

linha = {
    "id_video":          v["id"],
    "titulo":            snippet["title"],
    "descricao":         re.sub(r"\s+", " ", snippet.get("description", "")).strip(),
    "canal":             snippet["channelTitle"],
    "data_publicacao":   iso(snippet.get("publishedAt")),
    "data_inicio_live":  iso(live.get("actualStartTime")),
    "espectadores_atuais": live.get("concurrentViewers", ""),
}

# SALVA/ATUALIZA CSV
gravar_cabecalho = not os.path.exists(ARQ_CSV)
with open(ARQ_CSV, "a", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=CAMPOS)
    if gravar_cabecalho:
        wr.writeheader()
    wr.writerow(linha)

print(f"✅ Dados gravados em {ARQ_CSV}")

# -*- coding: utf-8 -*-
import os, sys, csv, re
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from googleapiclient.discovery import build

ARQ_CSV = "metadados_video.csv"
CAMPOS = [
    "id_video", "titulo", "descricao", "url",
    "canal", "data_publicacao",
    "data_inicio_live", "espectadores_atuais",
    "views", "likes", "comentarios"
]

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise RuntimeError("Defina YOUTUBE_API_KEY no .env")

youtube = build("youtube", "v3", developerKey=API_KEY)

# ───────── helpers ────────────────────────────────────────────
def extrair_id(url: str) -> str:
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    q = parse_qs(urlparse(url).query).get("v", [])
    return q[0] if q else url  # já é o próprio ID

def iso(dt):
    return dt if dt else ""

def num(valor):
    """Converte contagens numéricas para int ou '' se ausente."""
    return int(valor) if valor and valor.isdigit() else ""

# ───────── main ───────────────────────────────────────────────
if len(sys.argv) < 2:
    sys.exit("Passe a URL do vídeo como argumento!")

video_id = extrair_id(sys.argv[1])
print(f"🔍 Consultando vídeo {video_id}")

resp = youtube.videos().list(
    id=video_id,
    part="snippet,statistics,contentDetails,liveStreamingDetails"
).execute()

if not resp["items"]:
    raise ValueError("Vídeo não encontrado ou ID inválido.")

v = resp["items"][0]
snippet = v["snippet"]
stats   = v.get("statistics", {})
live    = v.get("liveStreamingDetails", {})

linha = {
    "id_video":           v["id"],
    "titulo":             snippet["title"],
    "descricao":          re.sub(r"\s+", " ", snippet.get("description", "")).strip(),
    "url":                f"https://www.youtube.com/watch?v={v['id']}",
    "canal":              snippet["channelTitle"],
    "data_publicacao":    iso(snippet.get("publishedAt")),
    "data_inicio_live":   iso(live.get("actualStartTime")),
    "espectadores_atuais": live.get("concurrentViewers", ""),
    "views":              num(stats.get("viewCount", "")),
    "likes":              num(stats.get("likeCount", "")),       # dislikeCount não é mais exposto
    "comentarios":        num(stats.get("commentCount", ""))
}

# ───────── grava / atualiza CSV ───────────────────────────────
cabecalho = not os.path.exists(ARQ_CSV)
with open(ARQ_CSV, "a", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=CAMPOS)
    if cabecalho:
        wr.writeheader()
    wr.writerow(linha)

print(f"Dados adicionados em {ARQ_CSV}")

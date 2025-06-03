# -*- coding: utf-8 -*-

import os, csv, time, re
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
import pandas as pd

# 1. CONFIGURAÇÕES E LISTA DE CANAIS
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise RuntimeError("Variável YOUTUBE_API_KEY não encontrada no .env")

youtube = build("youtube", "v3", developerKey=API_KEY)

# apelido : channelId
CANAIS = {
    "luangameplay":      "UCddN6tViXZMEOfvO-rqfbNg",
    "cavalao2":          "UCSl2-bnD5irdJkk7ejJS4ow",
    "biahkov":           "UCPTmDqH4cUbTJ_XABClIFlw",
    "fabiojunior":       "UC1WdbwLH7azQtv3BAnYt_vg",
    "diegosheipado":     "UC0Zhnj_IarrejROxchWtkMQ",
    "canaldoronaldinho": "UCjIN9CsGuLhj7NkNspZxw7g",
    "wallacegamer":      "UCb7JJAHkxdMVmFXw8tYDDdw",
    "renanplay":         "UCP-HJIRXN-apUPSCOehEDZw",
}

PASTA_SAIDA = "dados_calvoesfera"
os.makedirs(PASTA_SAIDA, exist_ok=True)

REGEX_NUM = re.compile(r"[^\d]")

def limpa_num(s):
    """Remove separadores e devolve int."""
    if s is None:
        return 0
    return int(REGEX_NUM.sub("", str(s)) or 0)

# 2. LOOP SOBRE CANAIS
resumo_canais = []

for apelido, canal_id in CANAIS.items():
    print(f"🔍 Coletando: {apelido}")

    # 2.1 vídeos do canal, ordenados por data
    search_params = {
        "channelId": canal_id,
        "part": "id",
        "maxResults": 50,
        "order": "date",
        "type": "video",
    }

    all_video_ids = []
    search_resp = youtube.search().list(**search_params).execute()
    while True:
        for item in search_resp.get("items", []):
            all_video_ids.append(item["id"]["videoId"])
        if "nextPageToken" not in search_resp:
            break
        search_params["pageToken"] = search_resp["nextPageToken"]
        search_resp = youtube.search().list(**search_params).execute()
        time.sleep(1)       # evita rate-limit leve

    print(f"   → {len(all_video_ids)} vídeos encontrados")

    # 2.2 estatísticas em lotes de 50
    detalhes_videos = []
    for i in range(0, len(all_video_ids), 50):
        ids_lote = all_video_ids[i : i + 50]
        resp = youtube.videos().list(
            id=",".join(ids_lote),
            part="snippet,statistics,contentDetails,liveStreamingDetails",
        ).execute()

        for v in resp.get("items", []):
            snippet = v["snippet"]
            data_pub = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            if data_pub.year != 2025:
                continue  # só 2025

            titulo = snippet["title"]
            url = f"https://www.youtube.com/watch?v={v['id']}"
            views = limpa_num(v.get("statistics", {}).get("viewCount"))
            duracao = v["contentDetails"].get("duration", "")
            tipo = snippet.get("liveBroadcastContent", "none")  # 'live', 'none', 'upcoming'

            detalhes_videos.append(
                [titulo, data_pub.isoformat(), url, views, duracao, tipo]
            )
        time.sleep(1)

    # 2.3 salva CSV detalhado por canal
    nome_csv = os.path.join(PASTA_SAIDA, f"detalhes_{apelido}_2025.csv")
    with open(nome_csv, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["Título", "Data", "URL", "Visualizações", "Duração", "Tipo"])
        wr.writerows(detalhes_videos)
    print(f"   → {len(detalhes_videos)} vídeos de 2025 salvos em {nome_csv}")

    # 2.4 busca inscritos dinâmicos
    chan_resp = youtube.channels().list(id=canal_id, part="statistics").execute()
    inscritos = limpa_num(chan_resp["items"][0]["statistics"]["subscriberCount"])

    # 2.5 sumariza
    total_views = sum(x[3] for x in detalhes_videos)
    resumo_canais.append(
        {
            "Canal": apelido,
            "Lives 2025": len(detalhes_videos),
            "Views 2025": total_views,
            "Inscritos (atual)": inscritos,
        }
    )

# 3. RELATÓRIO FINAL
df = pd.DataFrame(resumo_canais).sort_values("Views 2025", ascending=False)
df.to_csv(os.path.join(PASTA_SAIDA, "resumo_calvoesfera_2025.csv"), index=False)

print("\n🏁 Processamento concluído.")
print(df.to_string(index=False))

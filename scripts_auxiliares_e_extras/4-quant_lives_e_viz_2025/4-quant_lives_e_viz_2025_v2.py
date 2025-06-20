# -*- coding: utf-8 -*-
import os, csv, time, re
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
import pandas as pd
import isodate

# 1 ─ CONFIGURAÇÃO GERAL
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise RuntimeError("Variável YOUTUBE_API_KEY não encontrada no .env")

youtube = build("youtube", "v3", developerKey=API_KEY)

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
    return int(REGEX_NUM.sub("", str(s)) or 0) if s else 0

# 2 ─ FUNÇÕES AUXILIARES
def eh_live_gravada(video):
    lsd = video.get("liveStreamingDetails", {})
    return bool(lsd.get("actualStartTime") or lsd.get("scheduledStartTime"))

def duracao_em_segundos(iso):
    try:
        return int(isodate.parse_duration(iso).total_seconds())
    except Exception:
        return 0

# 3 ─ COLETA E PROCESSAMENTO
resumo_canais = []

for apelido, canal_id in CANAIS.items():
    print(f"Coletando: {apelido}")

    # 3.1 – busca todos os IDs de vídeos do canal
    search_params = dict(
        channelId=canal_id,
        part="id",
        maxResults=50,
        order="date",
        type="video",
    )
    ids = []
    resp = youtube.search().list(**search_params).execute()
    while True:
        ids.extend(item["id"]["videoId"] for item in resp.get("items", []))
        if "nextPageToken" not in resp:
            break
        search_params["pageToken"] = resp["nextPageToken"]
        resp = youtube.search().list(**search_params).execute()
        time.sleep(1)

    # 3.2 – coleta metadados em lotes
    detalhes = []
    live_views_2025 = 0
    total_views_2025 = 0
    lives_2025 = 0

    for i in range(0, len(ids), 50):
        lote = ",".join(ids[i:i+50])
        vresp = youtube.videos().list(
            id=lote,
            part="snippet,statistics,contentDetails,liveStreamingDetails,recordingDetails",
        ).execute()

        for v in vresp.get("items", []):
            snippet = v["snippet"]
            data_pub = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            if data_pub.year != 2025:
                continue

            views = limpa_num(v.get("statistics", {}).get("viewCount"))
            total_views_2025 += views

            flag_live = eh_live_gravada(v)
            if flag_live:
                live_views_2025 += views
                lives_2025 += 1

            detalhes.append([
                snippet["title"],
                data_pub.isoformat(),
                f"https://www.youtube.com/watch?v={v['id']}",
                views,
                duracao_em_segundos(v["contentDetails"].get("duration", "")),
                "live" if flag_live else "upload",
            ])
        time.sleep(1)

    # # 3.3 – salva CSV com TODOS os vídeos de 2025
    # arq_csv = os.path.join(PASTA_SAIDA, f"detalhes_{apelido}_2025.csv")
    # with open(arq_csv, "w", newline="", encoding="utf-8") as f:
    #     wr = csv.writer(f)
    #     wr.writerow(["Título", "Data", "URL", "Visualizações", "Duração (s)", "Foi Live?"])
    #     wr.writerows(detalhes)
    # print(f"   → {len(detalhes)} vídeos de 2025 salvos em {arq_csv}")

    # 3.4 – info de inscritos para o resumo
    subs = youtube.channels().list(id=canal_id, part="statistics").execute()
    inscritos = limpa_num(subs["items"][0]["statistics"]["subscriberCount"])

    resumo_canais.append({
        "Canal": apelido,
        "Lives 2025": lives_2025,
        "Views Lives 2025": live_views_2025,
        "Views Totais 2025": total_views_2025,
        "Inscritos (atual)": inscritos,
    })

# 4 ─ RELATÓRIO FINAL
df = (pd.DataFrame(resumo_canais)
        .sort_values("Views Totais 2025", ascending=False)
        .reset_index(drop=True))

# salva o resumo
arq_resumo = os.path.join(PASTA_SAIDA, "resumo_canais_2025.csv")
df.to_csv(arq_resumo, index=False, encoding="utf-8")
print(f"\nResumo salvo em {arq_resumo}")

# (opcional) exibir no prompt
print(df.to_string(index=False))


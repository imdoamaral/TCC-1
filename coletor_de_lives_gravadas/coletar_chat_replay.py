#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coletar_chat_replay.py
Baixa o replay de chat de uma live gravada do YouTube.

"""
import os
import re
import sys
import csv
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import pandas as pd
from chat_downloader import ChatDownloader
from yt_dlp import YoutubeDL

INTERVALO_GRAVACAO = 100_000 # grava num CSV se o total chega em 100.000 mensagens
DIRETORIO_BASE = "dados"

# utilidades
def gerar_nome_pasta(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", texto).strip("_") or "canal_desconhecido"


def extrair_id_yt(url_ou_id: str) -> tuple[str, str]:
    """Retorna (id_video, url_para_info) aceitando ID puro, /watch?v=… ou /live/…"""
    # ID puro (11 caracteres)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_ou_id):
        return url_ou_id, f"https://www.youtube.com/watch?v={url_ou_id}"

    p = urlparse(url_ou_id)

    qs_id = parse_qs(p.query).get("v", [None])[0]
    if qs_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", qs_id):
        return qs_id, url_ou_id.split("&")[0]

    last = p.path.rstrip("/").split("/")[-1]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", last):
        return last, url_ou_id.split("?")[0]

    return url_ou_id, url_ou_id


def obter_metadados_video(id_video: str, url_para_info: str) -> dict:
    padrao = {
        "id_video": id_video,
        "titulo": "",
        "descricao": "",
        "canal": "",
        "data_publicacao": "",
        "data_inicio_live": "",
        "espectadores_atuais": "",
        "likes": 0,
        "visualizacoes": 0,
        "comentarios": 0,
    }

    def ts_iso(seg: int | None) -> str:
        if not seg:
            return ""
        return datetime.fromtimestamp(seg, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url_para_info, download=False)
    except Exception as e:
        print(f"[aviso] yt-dlp não conseguiu ler metadados: {e}")
        return padrao

    pub_iso = ""
    if info.get("upload_date"): # YYYYMMDD
        pub_iso = datetime.strptime(info["upload_date"], "%Y%m%d")\
                         .strftime("%Y-%m-%dT00:00:00Z")

    return {
        "id_video":            id_video,
        "titulo":              info.get("title", ""),
        "descricao":           info.get("description", ""),
        "canal":               info.get("uploader") or info.get("channel", ""),
        "data_publicacao":     pub_iso,
        "data_inicio_live":    ts_iso(info.get("release_timestamp")
                                   or info.get("live_start_timestamp")),
        "espectadores_atuais": "", # não vale para replay
        "likes":               int(info.get("like_count", 0)),
        "visualizacoes":       int(info.get("view_count", 0)),
        "comentarios":         int(info.get("comment_count", 0)),
    }


def normalizar_timestamp(raw_ts: float | int) -> float:
    """
    Converte o timestamp do chat-downloader (µs ou ms) para segundos.
      ≥1e14 → microsegundos   (div /1e6)
      ≥1e11 → milissegundos   (div /1e3)
      caso contrário assume já estar em segundos
    """
    if raw_ts >= 1e14: # 100 000 000 000 000
        return raw_ts / 1_000_000
    if raw_ts >= 1e11: # 100 000 000 000
        return raw_ts / 1_000
    return raw_ts


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python coletar_chat_replay.py <URL ou ID do vídeo>")
        sys.exit(1)

    raw_arg = sys.argv[1].strip()
    id_video, url_info = extrair_id_yt(raw_arg)

    # 1) metadados
    meta = obter_metadados_video(id_video, url_info)

    canal_limpo = gerar_nome_pasta(meta["canal"])
    if meta["data_publicacao"]:
        data_base = meta["data_publicacao"][:10]
        hora_base = "00-00-00"
    else:
        agora = datetime.utcnow().strftime("%Y-%m-%d__%H-%M-%S")
        data_base, hora_base = agora.split("__")

    pasta_dest = os.path.join(DIRETORIO_BASE, f"{canal_limpo}__{data_base}__{hora_base}__{id_video}")
    os.makedirs(pasta_dest, exist_ok=True)

    arq_meta = os.path.join(pasta_dest, "metadados.csv")
    arq_chat = os.path.join(pasta_dest, "chat.csv")

    with open(arq_meta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(meta.keys()))
        w.writeheader()
        w.writerow(meta)
    print(f"Metadados gravados em {arq_meta}")

    # 2) chat
    print("→ Iniciando download do chat (replay)…")

    chat = ChatDownloader().get_chat(raw_arg)

    buffer: list[dict] = []
    total = 0

    for msg in chat:
        try:
            ts_raw = msg["timestamp"] # micro ou mili-segundos
            seg = normalizar_timestamp(ts_raw)
            buffer.append({
                "id_video":  id_video,
                "timestamp": datetime.fromtimestamp(seg, tz=timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "autor":     msg.get("author", {}).get("name", ""),
                "mensagem":  msg.get("message", "")
            })
            total += 1
        except KeyError:
            continue

        if total % INTERVALO_GRAVACAO == 0:
            pd.DataFrame(buffer).to_csv(
                arq_chat,
                mode="a",
                index=False,
                header=not os.path.exists(arq_chat),
                encoding="utf-8"
            )
            buffer.clear()
            print(f"  {total} mensagens gravadas…")

    if buffer:
        pd.DataFrame(buffer).to_csv(
            arq_chat,
            mode="a",
            index=False,
            header=not os.path.exists(arq_chat),
            encoding="utf-8"
        )

    print(f"✓ Coleta concluída – {total} mensagens salvas em {arq_chat}")


if __name__ == "__main__":
    main()

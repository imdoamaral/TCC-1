#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capturador de chat ao vivo do YouTube.

Recebe o ID do vídeo como argumento, busca o `liveChatId`, grava metadados do
vídeo em CSV e, a cada 30 s, anexa novas mensagens no arquivo
``dados/<canal>__<data_inicio>__<hora_inicio>__<id_video>/chat.csv``.

Pré-requisitos:
    - google-api-python-client
    - pandas
    - yt_api_manager.py (mesmo diretório) + config.py
    - ser chamado pelo monitor ou manualmente:  ``python3 capturar_chat.py <ID>``

O script cria um arquivo-trava em ``dados/chats/trava_<id_video>`` para impedir
instâncias duplicadas e o remove ao terminar.
"""

from __future__ import annotations

import csv
import logging
import os
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from yt_api_manager import YouTubeAPIManager

# CONFIGURAÇÕES
INTERVALO_COLETA = 30 # segundos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

api_manager = YouTubeAPIManager.obter_instancia()

# FUNÇÕES AUXILIARES
def slugify(texto: str) -> str:
    """Remove acentos e caracteres proibidos para usar em nomes de pasta."""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in texto)


def split_iso_datetime(iso_str: str) -> Tuple[str, str]:
    """Devolve (YYYY-MM-DD, HH-MM-SS) a partir de uma string ISO-8601."""
    if not iso_str:
        return "", ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H-%M-%S")
    except Exception:
        return iso_str[:10], iso_str[11:19].replace(":", "-")


def caminho_trava(id_video: str) -> Path:
    return Path("dados") / "chats" / f"trava_{id_video}"


def remover_trava(id_video: str) -> None:
    """Exclui o arquivo-trava (usado pelo monitor)."""
    try:
        caminho_trava(id_video).unlink(missing_ok=True)
    except Exception as exc:  # pragma: no cover
        log.warning("Erro ao remover trava: %s", exc)


# CHAMADAS À API / METADADOS
def obter_chat_e_metadados(id_video: str) -> Tuple[str | None, Dict | None]:
    """Retorna (liveChatId, metadados) ou (None, None) se não achar/live offline."""
    resp = api_manager.executar_requisicao(
        lambda cli, **kw: cli.videos().list(**kw),
        part="snippet,liveStreamingDetails",
        id=id_video,
    )
    itens = resp.get("items")
    if not itens:
        log.error("Vídeo %s não encontrado.", id_video)
        return None, None

    item = itens[0]
    detalhes = item.get("liveStreamingDetails", {})
    id_chat = detalhes.get("activeLiveChatId") or detalhes.get("liveChatId")
    if not id_chat:
        log.error("O vídeo %s não possui chat ao vivo.", id_video)
        return None, None

    meta = {
    "id_video"           : id_video,
    "titulo"             : item["snippet"].get("title", ""),
    "descricao"          : item["snippet"].get("description", ""),
    "canal"              : item["snippet"].get("channelTitle", ""),
    "data_publicacao"    : item["snippet"].get("publishedAt", ""),
    "data_inicio_live"   : detalhes.get("actualStartTime", ""),
    "espectadores_atuais": detalhes.get("concurrentViewers", ""),
    "likes"              : int(item.get("statistics", {}).get("likeCount", 0)),
    "visualizacoes"      : int(item.get("statistics", {}).get("viewCount", 0)),
    "comentarios"        : int(item.get("statistics", {}).get("commentCount", 0)),
    }
    return id_chat, meta


# MAIN
def main() -> None:
    if len(sys.argv) < 2:
        log.error("Uso: python3 capturar_chat.py <ID_VIDEO>")
        sys.exit(1)

    id_video = sys.argv[1]
    id_chat, meta = obter_chat_e_metadados(id_video)
    if not id_chat:
        sys.exit(1)

    # Diretório de saída
    data_fmt, hora_fmt = split_iso_datetime(meta["data_inicio_live"])
    pasta_live = (
        Path("dados")
        / f"{slugify(meta['canal'])}__{data_fmt}__{hora_fmt}__{id_video}"
    )
    pasta_live.mkdir(parents=True, exist_ok=True)
    arq_chat = pasta_live / "chat.csv"
    arq_meta = pasta_live / "metadados.csv"

    # Salva metadados (linha única)
    with arq_meta.open("w", newline="", encoding="utf-8") as fp:
        csv.DictWriter(fp, fieldnames=meta.keys()).writerow(meta)

    log.info("Capturando chat de '%s' (%s)…", meta["titulo"], id_video)
    mensagens: List[Dict] = []
    proximo_token: str | None = None
    msgs_sem_texto = 0

    try:
        while True:
            resp = api_manager.executar_requisicao(
                lambda cli, **kw: cli.liveChatMessages().list(**kw),
                liveChatId=id_chat,
                part="snippet,authorDetails",
                maxResults=200,
                pageToken=proximo_token,
            )

            for item in resp["items"]:
                texto = item["snippet"].get("displayMessage")
                if texto:
                    mensagens.append(
                        {
                            "id_video": id_video,
                            "timestamp": item["snippet"]["publishedAt"],
                            "autor": item["authorDetails"]["displayName"],
                            "mensagem": texto,
                        }
                    )
                else:
                    msgs_sem_texto += 1

            # Salva lote a cada iteração
            if mensagens:
                df_novo = pd.DataFrame(mensagens)
                if arq_chat.exists():
                    df_novo = pd.concat([pd.read_csv(arq_chat), df_novo]).drop_duplicates(
                        subset=["timestamp", "autor", "mensagem"]
                    )
                df_novo.to_csv(arq_chat, index=False, encoding="utf-8")
                log.info("Mensagens acumuladas: %d", len(df_novo))
                mensagens.clear()

            proximo_token = resp.get("nextPageToken")

            if msgs_sem_texto:
                log.debug("%d mensagens sem texto ignoradas.", msgs_sem_texto)
                msgs_sem_texto = 0

            time.sleep(INTERVALO_COLETA)

    except KeyboardInterrupt:
        log.info("Captura interrompida pelo usuário.")
    except Exception as exc: # pragma: no cover
        log.error("Erro durante a captura: %s", exc)
    finally:
        remover_trava(id_video)


if __name__ == "__main__":
    main()

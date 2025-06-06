#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor contínuo de lives em canais do YouTube.

— Percorre a lista em ``../canais.txt`` a cada N minutos.
— Quando detecta uma nova live:
      1. Salva metadados em ``../dados/metadados/``.
      2. Dispara ``capturar_chat.py`` em subprocesso para baixar o chat.
— Usa ``YouTubeAPIManager`` (singleton) para compartilhar a rotação de chaves.

Requer:
    - google-api-python-client
    - yt_api_manager.py e config.py no mesmo diretório
    - canais.txt (um id ou URL de canal por linha)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from yt_api_manager import YouTubeAPIManager

# CONFIGURAÇÕES
INTERVALO_CURTO = 600     # segundos (22h–0h: checagem a cada 10 min)
INTERVALO_LONGO = 3600    # segundos (demais horários: checagem a cada 1 h)

# Nível de log (DEBUG, INFO, WARNING…)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Instância única para revezar as chaves
api_manager = YouTubeAPIManager.obter_instancia()

# FUNÇÕES UTILITÁRIAS
def obter_intervalo() -> int:
    """Define o intervalo de varredura conforme o horário (dia/noite)."""
    hora = datetime.now().hour
    return INTERVALO_CURTO if hora >= 21 or hora <= 0 else INTERVALO_LONGO


def registrar_consumo(qtd_busca: int = 0, qtd_metadados: int = 0) -> None:
    """Grava consumo aproximado de quota num arquivo diário."""
    hoje = datetime.now().strftime("%Y%m%d")
    caminho = Path("log_consumo_{}.txt".format(hoje))
    pontos = qtd_busca * 100 + qtd_metadados
    with caminho.open("a", encoding="utf-8") as fp:
        fp.write(
            f"{datetime.now().isoformat()} BUSCA:{qtd_busca} "
            f"METADADOS:{qtd_metadados} TOTAL:{pontos}\n"
        )


def criar_estruturas_pastas(base: Path) -> None:
    (base / ".." / "dados" / "chats").mkdir(parents=True, exist_ok=True)
    (base / ".." / "dados" / "metadados").mkdir(parents=True, exist_ok=True)


def carregar_canais(base: Path) -> List[str]:
    arquivo = base / ".." / "canais.txt"
    with arquivo.open(encoding="utf-8") as fp:
        return [linha.strip() for linha in fp if linha.strip()]


# CHAMADAS À API (WRAPPERS)
def buscar_lives_ativas(id_canal: str) -> List[Tuple[str, str]]:
    """Retorna pares (id_video, título) de lives ao vivo no canal."""
    resp = api_manager.executar_requisicao(
        lambda cli, **kw: cli.search().list(**kw),
        part="id,snippet",
        channelId=id_canal,
        eventType="live",
        type="video",
        maxResults=1,
    )

    return [
        (item["id"]["videoId"], item["snippet"]["title"])
        for item in resp.get("items", [])
    ]


def buscar_metadados(id_video: str) -> Dict:
    resp = api_manager.executar_requisicao(
        lambda cli, **kw: cli.videos().list(**kw),
        part="snippet,liveStreamingDetails",
        id=id_video,
    )
    items = resp.get("items")
    if not items:
        return {}
    item = items[0]
    detalhes = item.get("liveStreamingDetails", {})
    return {
        "id_video": id_video,
        "titulo": item["snippet"].get("title", ""),
        "descricao": item["snippet"].get("description", ""),
        "canal": item["snippet"].get("channelTitle", ""),
        "data_publicacao": item["snippet"].get("publishedAt", ""),
        "data_inicio_live": detalhes.get("actualStartTime", ""),
        "espectadores_atuais": detalhes.get("concurrentViewers", ""),
    }


def live_ainda_ativa(id_video: str) -> bool:
    """Confere se a live já terminou (campo actualEndTime)."""
    resp = api_manager.executar_requisicao(
        lambda cli, **kw: cli.videos().list(**kw),
        part="liveStreamingDetails",
        id=id_video,
    )
    items = resp.get("items")
    if not items:
        return False
    details = items[0].get("liveStreamingDetails", {})
    return "actualEndTime" not in details


# CONTROLE DE TRAVAS
def caminho_trava(id_video: str, base: Path) -> Path:
    return base / ".." / "dados" / "chats" / f"trava_{id_video}"


def trava_ativa(id_video: str, base: Path) -> bool:
    """Verifica se já existe processo capturando esse chat."""
    arq = caminho_trava(id_video, base)
    if not arq.exists():
        return False
    try:
        pid = int(arq.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def criar_trava(id_video: str, base: Path) -> None:
    caminho_trava(id_video, base).write_text(str(os.getpid()))


# ROTINAS DE CAPTURA
def salvar_metadados(id_video: str, dados: Dict, base: Path) -> None:
    arq = base / ".." / "dados" / "metadados" / f"metadados_{id_video}.json"
    with arq.open("w", encoding="utf-8") as fp:
        json.dump(dados, fp, ensure_ascii=False, indent=2)


def iniciar_captura_chat(id_video: str, base: Path) -> None:
    if trava_ativa(id_video, base):
        log.info("Chat %s já está sendo capturado.", id_video)
        return

    criar_trava(id_video, base)
    subprocess.Popen(
        [sys.executable, base / "capturar_chat.py", id_video],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log.info("Captura do chat iniciada para %s", id_video)


# MAIN
def main() -> None:
    base_dir = Path(__file__).resolve().parent
    criar_estruturas_pastas(base_dir)
    canais = carregar_canais(base_dir)
    canais_em_live: Dict[str, str] = {}

    log.info("Monitorando %d canais…", len(canais))
    while True:
        q_busca = q_meta = 0

        for canal in canais:
            # Se o canal já estava em live, verifique se terminou
            if canal in canais_em_live and not live_ainda_ativa(canais_em_live[canal]):
                log.info("Live %s finalizada.", canais_em_live[canal])
                canais_em_live.pop(canal)

            # Procura lives novas
            for vid, titulo in buscar_lives_ativas(canal):
                q_busca += 1
                if trava_ativa(vid, base_dir):
                    continue

                log.info("Nova live: %s — %s", canal, titulo)
                meta = buscar_metadados(vid)
                q_meta += 1
                if meta:
                    salvar_metadados(vid, meta, base_dir)
                iniciar_captura_chat(vid, base_dir)
                canais_em_live[canal] = vid

        registrar_consumo(q_busca, q_meta)
        intervalo = obter_intervalo()
        log.info("Aguardando %d min…\n", intervalo // 60)
        time.sleep(intervalo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Monitor interrompido pelo usuário.")

# -*- coding: utf-8 -*-

"""
Monitor contínuo de lives em canais do YouTube.

• Percorre a lista em ``../canais.txt`` a cada N minutos.
• Quando detecta uma live:
    1. Salva metadados em ``../dados/metadados/``.
    2. Dispara ``capturar_chat.py`` em subprocesso para baixar o chat.
• Usa ``YouTubeAPIManager`` (singleton) para rotação de chaves.

Requer:
    - google-api-python-client, rich
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
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table
from yt_api_manager import YouTubeAPIManager

# LOGGING
logging.getLogger("googleapiclient.http").setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# CONFIG
INTERVALO_CURTO = 600   # seg (22 h–0 h)
INTERVALO_LONGO = 3600  # seg (resto do dia)

api_manager = YouTubeAPIManager.obter_instancia()
console = Console()

# FUNÇÕES UTIL
def obter_intervalo() -> int:
    hora = datetime.now().hour
    return INTERVALO_CURTO if hora >= 21 or hora <= 0 else INTERVALO_LONGO


def registrar_consumo(q_busca: int, q_meta: int) -> None:
    hoje = datetime.now().strftime("%Y%m%d")
    arq = Path(f"log_consumo_{hoje}.txt")
    pontos = q_busca * 100 + q_meta
    with arq.open("a", encoding="utf-8") as fp:
        fp.write(f"{datetime.now().isoformat()} BUSCA:{q_busca} "
                 f"METADADOS:{q_meta} TOTAL:{pontos}\n")


def criar_estruturas_pastas(base: Path) -> None:
    (base / ".." / "dados" / "chats").mkdir(parents=True, exist_ok=True)
    (base / ".." / "dados" / "metadados").mkdir(parents=True, exist_ok=True)


def carregar_canais(base: Path) -> List[str]:
    arq = base / ".." / "canais.txt"
    with arq.open(encoding="utf-8") as fp:
        return [l.strip() for l in fp if l.strip()]


def gerar_nome_pasta(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in texto) or "canal"

# API WRAPPERS
def buscar_lives_ativas(canal_id: str) -> List[Tuple[str, str]]:
    resp = api_manager.executar_requisicao(
        lambda c, **kw: c.search().list(**kw),
        part="id,snippet",
        channelId=canal_id,
        eventType="live",
        type="video",
        maxResults=1,
    )
    return [
        (it["id"]["videoId"], it["snippet"]["title"])
        for it in resp.get("items", [])
    ]


def buscar_metadados(id_video: str) -> Dict:
    resp = api_manager.executar_requisicao(
        lambda c, **kw: c.videos().list(**kw),
        part="snippet,liveStreamingDetails,statistics",
        id=id_video,
    )
    itens = resp.get("items")
    if not itens:
        return {}
    item = itens[0]
    det  = item.get("liveStreamingDetails", {})
    stat = item.get("statistics", {})
    return {
        "id_video":            id_video,
        "titulo":              item["snippet"].get("title", ""),
        "descricao":           item["snippet"].get("description", ""),
        "canal":               item["snippet"].get("channelTitle", ""),
        "data_publicacao":     item["snippet"].get("publishedAt", ""),
        "data_inicio_live":    det.get("actualStartTime", ""),
        "espectadores_atuais": det.get("concurrentViewers", ""),
        "likes":               int(stat.get("likeCount", 0)),
        "visualizacoes":       int(stat.get("viewCount", 0)),
        "comentarios":         int(stat.get("commentCount", 0)),
    }


def live_ainda_ativa(id_video: str) -> bool:
    resp = api_manager.executar_requisicao(
        lambda c, **kw: c.videos().list(**kw),
        part="liveStreamingDetails",
        id=id_video,
    )
    itens = resp.get("items")
    if not itens:
        return False
    det = itens[0].get("liveStreamingDetails", {})
    return "actualEndTime" not in det

# TRAVAS DE CHAT
def caminho_trava(id_video: str, base: Path) -> Path:
    return base / ".." / "dados" / "chats" / f"trava_{id_video}"


def trava_ativa(id_video: str, base: Path) -> bool:
    p = caminho_trava(id_video, base)
    if not p.exists():
        return False
    try:
        pid = int(p.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def criar_trava(id_video: str, base: Path) -> None:
    caminho_trava(id_video, base).write_text(str(os.getpid()))

# CAPTURA CHAT
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

# STATUS NO TERMINAL
def exibir_status(vivos: Dict[str, Dict]) -> None:
    console.clear()
    if not vivos:
        console.print("[bold yellow]Nenhuma live ativa[/]")
        return

    tabela = Table(title="Lives ativas", header_style="bold magenta")
    tabela.add_column("Canal")
    tabela.add_column("Título (até 60 car.)")
    tabela.add_column("Duração", justify="right")

    for info in vivos.values():
        dur = datetime.now() - info["inicio"]
        hh, rem = divmod(int(dur.total_seconds()), 3600)
        mm = rem // 60
        tabela.add_row(info["canal_nome"], info["titulo"], f"{hh:02d}:{mm:02d}")

    console.print(tabela)

# MAIN
def main() -> None:
    base_dir = Path(__file__).resolve().parent
    criar_estruturas_pastas(base_dir)
    canais = carregar_canais(base_dir)

    # canal_id → {vid, inicio, canal_nome, titulo}
    vivos: Dict[str, Dict] = {}

    log.info("Monitorando %d canais…", len(canais))
    while True:
        q_busca = q_meta = 0

        for canal in canais:
            # se já há live, verifique se terminou
            if canal in vivos:
                if live_ainda_ativa(vivos[canal]["vid"]):
                    continue
                log.info("Live %s finalizada.", vivos[canal]["vid"])
                vivos.pop(canal, None)

            # buscar novas lives
            q_busca += 1
            for vid, titulo in buscar_lives_ativas(canal):
                if trava_ativa(vid, base_dir):
                    continue

                meta = buscar_metadados(vid)
                q_meta += 1
                if meta:
                    salvar_metadados(vid, meta, base_dir)

                log.info("Nova live: %s — %s", meta["canal"], titulo)
                iniciar_captura_chat(vid, base_dir)

                vivos[canal] = {
                    "vid": vid,
                    "inicio": datetime.now(),
                    "canal_nome": meta["canal"],
                    "titulo": titulo[:60],
                }

        exibir_status(vivos)
        registrar_consumo(q_busca, q_meta)

        intervalo = obter_intervalo()
        log.info("Aguardando %d min…\n", intervalo // 60)
        time.sleep(intervalo)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Monitor interrompido pelo usuário.")

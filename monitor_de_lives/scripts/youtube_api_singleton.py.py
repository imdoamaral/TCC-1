# -*- coding: utf-8 -*-

"""
Gerencia a rotação de chaves da API do YouTube.

Mantém uma instância única (Singleton) para que todo o código compartilhe a
mesma cota e troca de chave automaticamente quando recebe quotaExceeded (HTTP 403).
"""

import time
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import yt_api_config

logger = logging.getLogger(__name__)


class YouTubeAPIManager:
    _instancia = None

    SERVICO = "youtube"
    VERSAO = "v3"

    def __init__(self, timeout: int | None = None) -> None:
        self._keys: list[str] = yt_api_config.youtube_keys
        self._timeout: int = timeout or getattr(yt_api_config, "try_again_timeout", 60)
        self._idx: int = -1
        self.youtube = self._novo_cliente()

    # Padrão Singleton
    @classmethod
    def obter_instancia(cls) -> "YouTubeAPIManager":
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    # Internos
    def _novo_cliente(self):
        """Cria e devolve um objeto `youtube` com a próxima chave."""
        self._idx = (self._idx + 1) % len(self._keys)
        chave = self._keys[self._idx]
        logger.info("Usando chave %d/%d", self._idx + 1, len(self._keys))
        return build(self.SERVICO, self.VERSAO, developerKey=chave, cache_discovery=False)

    # API pública
    def executar_requisicao(self, metodo, **kwargs):
        """
        Executa `metodo(youtube, **kwargs).execute()` trocando de chave caso
        receba erro de quota (403). Retorna o JSON da resposta.
        """
        while True:
            try:
                return metodo(self.youtube, **kwargs).execute()

            except HttpError as exc:
                quota = exc.resp.status == 403 and b"quotaExceeded" in exc.content
                if quota:
                    logger.warning("Quota estourada — trocando de chave…")
                    self.youtube = self._novo_cliente()
                    continue

                if exc.resp.status in (500, 503):
                    logger.warning("Erro %s — tentando novamente em %ss",
                                   exc.resp.status, self._timeout)
                    time.sleep(self._timeout)
                    continue

                raise

# -*- coding: utf-8 -*-

"""
Arquivo de configuração do coletor de lives.

- youtube_keys: lista de chaves da API que serão usadas em rotação.
  Adicione novas chaves mantendo o formato exato (strings).
  ⚠️  NÃO versionar este arquivo em repositórios públicos.

- try_again_timeout: segundos entre novas tentativas em erros 5xx.
"""

youtube_keys = [
    "SUA_CHAVE_AQUI",
    "SUA_OUTRA_CHAVE_AQUI"
    # ...adicionar outras chaves aqui
]

try_again_timeout = 60  # segundos de espera antes de nova tentativa

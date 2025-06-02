import sys, os, re, html, glob
from yt_dlp import YoutubeDL

# 1. URL do vídeo
url = sys.argv[1] if len(sys.argv) > 1 else \
      'https://youtu.be/dK1ZOCCbEDI?si=cn5LRVhjVyEpwR2A'

# 2. Opções do yt-dlp: baixa só a legenda .vtt em português
ydl_opts = {
    'skip_download': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['pt'],
    'outtmpl': '%(title)s.%(ext)s',
}

# 3. Baixa a legenda
with YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])

# 4. Converte todos os .vtt recém-baixados para .txt
def vtt_to_txt(vtt_path):
    """
    Converte um arquivo .vtt em texto simples, removendo:
      • cabeçalho WEBVTT/Kind/Language
      • linhas de time-code
      • tags <00:00:00.000><c>…</c> e afins
      • duplicatas consecutivas
    Retorna o caminho do .txt gerado.
    """
    txt_path = os.path.splitext(vtt_path)[0] + '.txt'
    last = ''
    out_lines = []

    with open(vtt_path, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')

            # ignora cabeçalhos e linhas vazias
            if line.startswith(('WEBVTT', 'Kind:', 'Language:')) or not line:
                continue
            # ignora time-codes
            if '-->' in line:
                continue

            # remove marcas de posição/estilo
            line = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)  # <00:00:00.000>
            line = re.sub(r'</?c[^>]*>', '', line)                 # <c>…</c>
            line = re.sub(r'</?i>', '', line)                      # itálico
            line = html.unescape(line).strip()

            # evita linhas duplicadas em sequência
            if line and line != last:
                out_lines.append(line)
                last = line

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

    return txt_path

for vtt in glob.glob('*.vtt'):
    txt = vtt_to_txt(vtt)
    print(f'Legenda convertida: {txt}')


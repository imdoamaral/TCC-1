from yt_dlp import YoutubeDL

url = 'https://www.youtube.com/live/9-ad9G6kxDM?si=mVxa2LMetIHwBj1F'

ydl_opts = {
    'skip_download': True,
    'quiet': True,
}

with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    print("Canal:", info.get('channel'))
    print("Título:", info['title'])
    print("Likes:", info.get('like_count'))
    print("Views:", info['view_count'])
    print("Descrição:", info['description'])
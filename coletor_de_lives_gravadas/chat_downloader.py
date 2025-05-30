"""
Código para coleta de mensagens do chat sem o uso da API oficial do Youtube.
"""

from chat_downloader import ChatDownloader

url = 'https://www.youtube.com/watch?v=9-ad9G6kxDM'
chat = ChatDownloader().get_chat(url)

for message in chat:
    chat.print_formatted(message)

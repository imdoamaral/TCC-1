from chat_downloader import ChatDownloader

url = 'https://www.youtube.com/watch?v=gwmtr7_qqck'
chat = ChatDownloader().get_chat(url)

for message in chat:
    chat.print_formatted(message)

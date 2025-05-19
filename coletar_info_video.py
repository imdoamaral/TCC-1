from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

options = Options()
options.add_argument("--headless")  # Comentar essa linha para ver o navegador rodando
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()

url = 'https://www.youtube.com/watch?v=YIRN1tA-cC8'
driver.get(url)

def get_text_or_default(by, selector, wait_time=10, default="Não encontrado"):
    try:
        el = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((by, selector))
        )
        return el.text
    except Exception:
        return default

# --- Nome do canal ---
canal = get_text_or_default(By.CSS_SELECTOR, '#channel-name #text a')
if canal == "Não encontrado":  # Tenta pegar sem o <a>
    canal = get_text_or_default(By.CSS_SELECTOR, '#channel-name #text')
print(f'Canal: {canal}')

# --- Inscritos ---
inscritos = get_text_or_default(By.CSS_SELECTOR, '#owner-sub-count')
print(f'Inscritos: {inscritos}')

# --- Likes ---
# Rola até o botão de like para garantir o carregamento
driver.execute_script("window.scrollTo(0, 500);")
time.sleep(2)
likes = "Não encontrado"
try:
    likes_elements = driver.find_elements(By.CSS_SELECTOR, 'div.yt-spec-button-shape-next__button-text-content')
    for el in likes_elements:
        # Ajuste o critério conforme seu padrão (ex: likes sempre vêm antes do botão "Compartilhar")
        if "mil" in el.text or el.text.isdigit():
            likes = el.text
            break
except Exception:
    pass
print(f'Likes: {likes}')

# --- Visualizações ---
visualizacoes = get_text_or_default(By.XPATH, "//span[contains(text(),'visualizações')]")
print(f'Visualizações: {visualizacoes}')

# --- Descrição ---
# Tenta clicar em "Mostrar mais" se existir
try:
    botao_mais = driver.find_element(By.CSS_SELECTOR, 'tp-yt-paper-button#expand')
    botao_mais.click()
    time.sleep(1)
except Exception:
    pass  # Não há botão ou não foi necessário

descricao = get_text_or_default(By.CSS_SELECTOR, 'span.yt-core-attributed-string--link-inherit-color')
print(f'Descrição: {descricao}')

# --- Comentários ---
# Rola até o final da página para garantir que comentários carreguem
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(4)

comentarios = []
try:
    comentarios_eles = driver.find_elements(By.CSS_SELECTOR, 'ytd-comment-thread-renderer #content-text span')
    for i, comentario in enumerate(comentarios_eles[:3]):
        comentarios.append(comentario.text)
        print(f'Comentário {i+1}: {comentario.text}')
except Exception:
    print('Comentários: Não encontrados')

driver.quit()

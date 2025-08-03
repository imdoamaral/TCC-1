import pandas as pd
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# # Downloads do NLTK (só precisa uma vez)
# nltk.download('punkt')
# nltk.download('stopwords')

# Carrega a lista padrão de stopwords do NLTK.
stop_words_basicas = set(stopwords.words('portuguese'))
# Adicionamos algumas palavras muito comuns que poluem a análise
stop_words_basicas.update(['q', 'pra', 'tá', 'ta', 'https', 'https://', 'http', 'http://'])

# Carrega o dataset completo
print("Carregando dataset completo...")
df = pd.read_csv("/home/israel/Documentos/GitHub/dataset_unificado.csv")

print("Processando texto...")
texto_completo = ' '.join(df['mensagem'].dropna().astype(str).tolist())
palavras = word_tokenize(texto_completo.lower())

palavras_filtradas = []
for palavra in palavras:
    # Mantém apenas palavras com letras e que não estejam na lista BÁSICA de stopwords
    if palavra.isalpha() and len(palavra) > 2 and palavra not in stop_words_basicas:
        palavras_filtradas.append(palavra)

# Calcula a frequência das palavras
frequencia_palavras = nltk.FreqDist(palavras_filtradas)

# --- RESULTADO PRINCIPAL ---
print("\n--- AS 200 PALAVRAS MAIS FREQUENTES (ANTES DA LIMPEZA AGRESSIVA) ---")
print("Use esta lista para fazer a curadoria manual do seu dicionário.")
# A função most_common(200) retorna uma lista de tuplas (palavra, contagem)
top_200_palavras = frequencia_palavras.most_common(200)

# Imprime de uma forma fácil de ler e copiar
for palavra, contagem in top_200_palavras:
    print(f"{palavra}: {contagem}")
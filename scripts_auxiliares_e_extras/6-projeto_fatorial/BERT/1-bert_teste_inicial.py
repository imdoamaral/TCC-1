import pandas as pd
from transformers import BertTokenizer, BertForSequenceClassification

# 1. Carregar o nosso dataset
print("Carregando o dataset...")
df = pd.read_csv('amostra_rotulada.csv')
print("Dataset carregado com sucesso!")
print(df.head()) # Mostra as 5 primeiras linhas para verificar

# 2. Definir o nome do modelo que vamos usar
# Usaremos o 'BERTimbau Cased', treinado para o português do Brasil.
model_name = 'neuralmind/bert-base-portuguese-cased'

# 3. Carregar o Tokenizador específico deste modelo
print("\nCarregando o tokenizador do BERTimbau...")
tokenizer = BertTokenizer.from_pretrained(model_name)
print("Tokenizador carregado!")

# 4. Carregar o Modelo BERT pré-treinado
# BertForSequenceClassification é a arquitetura BERT com uma "cabeça" de classificação no topo.
# Ideal para tarefas como a nossa (classificar se um texto é tóxico ou não).
# a. num_labels=2: Informamos ao modelo que temos duas classes de saída (0 para 'Não Tóxico', 1 para 'Tóxico').
print("\nCarregando o modelo pré-treinado BERTimbau...")
model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2)
print("Modelo carregado!")

# Vamos testar o tokenizador com um exemplo simples
exemplo_texto = "Isso é apenas um teste para o tokenizador."
tokens = tokenizer.tokenize(exemplo_texto)

print(f"\nFrase original: '{exemplo_texto}'")
print(f"Frase tokenizada: {tokens}")
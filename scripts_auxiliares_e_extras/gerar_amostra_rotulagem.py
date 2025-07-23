import pandas as pd

# Carrega o dataset unificado
df = pd.read_csv("dataset_unificado.csv")

# Número de amostras por canal
n_por_canal = 500

# Seleciona a amostra estratificada (500 mensagens aleatórias de cada canal)
amostra = df.groupby('canal', group_keys=False).sample(n=n_por_canal, random_state=42)

# Garante que a coluna 'canal' está presente
amostra['canal'] = amostra['canal']

# Salva a amostra para rotulagem
amostra.to_csv("amostra_para_rotular.csv", index=False)

# Conta a quantidade de mensagens por canal e exibe
contagem = amostra['canal'].value_counts()
print("Quantidade de mensagens por canal na amostra:")
print(contagem)
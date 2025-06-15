import pandas as pd

# Carrega o dataset
df = pd.read_csv("dataset_unificado.csv")

# Mostra o cabeçalho (nomes das colunas)
print("Cabeçalho (nomes das colunas):")
print(list(df.columns))

# Mostra as primeiras 5 linhas como amostra
print("\nAmostra de 5 linhas:")
print(df.head())
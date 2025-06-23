import os
import pandas as pd

# Caminho base contendo as subpastas das lives
CAMINHO_DADOS = "/home/israel/Documentos/GitHub/dados"

# Lista para acumular os DataFrames combinados
todos_dados = []

# Percorre cada subpasta dentro de 'dados'
for nome_pasta in os.listdir(CAMINHO_DADOS):
    caminho_pasta = os.path.join(CAMINHO_DADOS, nome_pasta)
    
    if not os.path.isdir(caminho_pasta):
        continue

    caminho_chat = os.path.join(caminho_pasta, "chat.csv")
    caminho_meta = os.path.join(caminho_pasta, "metadados.csv")

    # Verifica se ambos os arquivos existem
    if not (os.path.isfile(caminho_chat) and os.path.isfile(caminho_meta)):
        print(f"Arquivos ausentes em: {nome_pasta}")
        continue

    try:
        df_chat = pd.read_csv(caminho_chat)
        df_meta = pd.read_csv(caminho_meta)

        # Espera-se que metadados tenha 1 linha. Repetir para cada linha do chat
        if len(df_meta) != 1:
            print(f"Metadados com {len(df_meta)} linhas em {nome_pasta}, pulando...")
            continue

        # Adiciona colunas de metadados (exceto 'descricao')
        for col in df_meta.columns:
            if col.lower() != "descricao":
                df_chat[col] = df_meta.iloc[0][col]


        todos_dados.append(df_chat)
    except Exception as e:
        print(f"Erro ao processar {nome_pasta}: {e}")

# Junta todos os dados em um único DataFrame
df_final = pd.concat(todos_dados, ignore_index=True)

# Salva o resultado no mesmo diretório do script
caminho_saida = os.path.join(os.getcwd(), "dataset_unificado.csv")
df_final.to_csv(caminho_saida, index=False)

print(f"- Arquivo gerado com sucesso: {caminho_saida}")
print(f"- Total de mensagens: {len(df_final)}")
print(f"- Total de transmissões: {len(todos_dados)}")

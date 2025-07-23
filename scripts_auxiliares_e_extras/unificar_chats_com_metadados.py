import os
import pandas as pd

# Intervalo desejado
DATA_INICIO = pd.to_datetime("2025-06-14T00:00:00+00:00")
DATA_FIM = pd.to_datetime("2025-07-14T23:59:59+00:00")

CAMINHO_DADOS = "/home/israel/Documentos/GitHub/dados"
todos_dados = []

for nome_pasta in os.listdir(CAMINHO_DADOS):
    caminho_pasta = os.path.join(CAMINHO_DADOS, nome_pasta)
    if not os.path.isdir(caminho_pasta):
        continue

    caminho_chat = os.path.join(caminho_pasta, "chat.csv")
    caminho_meta = os.path.join(caminho_pasta, "metadados.csv")

    if not (os.path.isfile(caminho_chat) and os.path.isfile(caminho_meta)):
        print(f"Arquivos ausentes em: {nome_pasta}")
        continue

    try:
        df_chat = pd.read_csv(caminho_chat)
        df_meta = pd.read_csv(caminho_meta)

        # Verifica se o início da live está dentro do intervalo
        if "data_inicio_live" in df_meta.columns:
            inicio_live = pd.to_datetime(df_meta.iloc[0]["data_inicio_live"], utc=True)
            if not (DATA_INICIO <= inicio_live <= DATA_FIM):
                continue
        else:
            print(f"Campo 'data_inicio_live' ausente em {nome_pasta}, pulando...")
            continue

        # Filtra as mensagens pelo intervalo de datas
        if "timestamp" in df_chat.columns:
            df_chat["timestamp"] = pd.to_datetime(df_chat["timestamp"], utc=True)
            df_chat = df_chat[
                (df_chat["timestamp"] >= DATA_INICIO) &
                (df_chat["timestamp"] <= DATA_FIM)
            ]

        if len(df_meta) != 1:
            print(f"Metadados com {len(df_meta)} linhas em {nome_pasta}, pulando...")
            continue

        for col in df_meta.columns:
            if col.lower() != "descricao":
                df_chat[col] = df_meta.iloc[0][col]

        if not df_chat.empty:
            todos_dados.append(df_chat)
    except Exception as e:
        print(f"Erro ao processar {nome_pasta}: {e}")

df_final = pd.concat(todos_dados, ignore_index=True)
caminho_saida = os.path.join(os.getcwd(), "dataset_unificado.csv")
df_final.to_csv(caminho_saida, index=False)

print(f"- Arquivo gerado com sucesso: {caminho_saida}")
print(f"- Total de mensagens: {len(df_final)}")
print(f"- Total de transmissões: {len(todos_dados)}")
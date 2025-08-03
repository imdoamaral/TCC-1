import pandas as pd

# --- PARÂMETROS DE CONFIGURAÇÃO ---

# Arquivo com as 17.415 mensagens coletadas dos picos de atividade
ARQUIVO_ENTRADA = "amostra_hotspots_para_rotular.csv"

# Nome do arquivo final que você irá rotular
ARQUIVO_SAIDA = "subamostra_hotspots_aleatoria.csv"

# Defina o tamanho final desejado para a sua amostra de hotspots.
# 2000 é um bom número para começar.
TAMANHO_DA_SUBAMOSTRA_FINAL = 2000

# --- FIM DA CONFIGURAÇÃO ---


try:
    print(f"Carregando a amostra de hotspots do arquivo: {ARQUIVO_ENTRADA}")
    df = pd.read_csv(ARQUIVO_ENTRADA)
    print(f"Total de mensagens no arquivo de entrada: {len(df)}")

    # Garante que não vamos tentar pegar uma amostra maior do que o arquivo contém
    n_amostras = min(len(df), TAMANHO_DA_SUBAMOSTRA_FINAL)

    if n_amostras < len(df):
        print(f"Selecionando uma subamostra aleatória de {n_amostras} mensagens...")
        # A única operação: pegar uma amostra aleatória simples do dataframe
        subamostra = df.sample(n=n_amostras, random_state=42)
    else:
        print("O número de mensagens já é menor ou igual ao tamanho desejado. Usando todas as mensagens.")
        subamostra = df

    print(f"Tamanho da subamostra final para rotulagem: {len(subamostra)}")
    
    # Adiciona as colunas de rotulagem se ainda não existirem
    if 'classificacao_binaria' not in subamostra.columns:
        subamostra['classificacao_binaria'] = ''
    if 'observacoes' not in subamostra.columns:
        subamostra['observacoes'] = ''
        
    subamostra.to_csv(ARQUIVO_SAIDA, index=False)
    print(f"Subamostra aleatória salva com sucesso em: '{ARQUIVO_SAIDA}'")

except FileNotFoundError:
    print(f"ERRO: O arquivo '{ARQUIVO_ENTRADA}' não foi encontrado.")
import pandas as pd
import re

# --- PARÂMETROS DE CONFIGURAÇÃO ---

# Seu dataset completo com mais de 1 milhão de mensagens
ARQUIVO_DE_DADOS = "dataset_unificado.csv"

# O arquivo de texto com seu dicionário de termos
ARQUIVO_DICIONARIO = "TCC-1/dicionario.txt"

# O tamanho da nova amostra que você quer gerar para rotular
TAMANHO_AMOSTRA_FINAL = 1000

# Nome do arquivo de saída com a nova amostra
ARQUIVO_SAIDA = "amostra_por_palavra_chave.csv"

# --- FIM DA CONFIGURAÇÃO ---

try:
    # 1. Carregar o dicionário de palavras-chave
    print(f"Carregando dicionário do arquivo: {ARQUIVO_DICIONARIO}")
    with open(ARQUIVO_DICIONARIO, 'r', encoding='utf-8') as f:
        # Lê cada linha, remove espaços em branco extras e ignora linhas vazias
        palavras_chave = [line.strip() for line in f if line.strip()]
    
    if not palavras_chave:
        print("ERRO: O arquivo de dicionário está vazio ou não foi encontrado.")
    else:
        print(f"{len(palavras_chave)} palavras-chave carregadas com sucesso.")

        # 2. Carregar o dataset completo
        print(f"Carregando dataset completo: {ARQUIVO_DE_DADOS}...")
        df_completo = pd.read_csv(ARQUIVO_DE_DADOS)
        
        # 3. Criar um padrão de regex para buscar todas as palavras-chave de uma vez
        # O `re.escape` garante que caracteres especiais nas palavras não quebrem o regex
        # O `|` funciona como um "OU"
        # `case=False` torna a busca insensível a maiúsculas/minúsculas
        padrao_regex = '|'.join(re.escape(palavra) for palavra in palavras_chave)
        print("Buscando por mensagens que contenham as palavras-chave...")
        
        # Filtra o dataframe, mantendo apenas as linhas que contêm pelo menos uma das palavras
        df_filtrado = df_completo[df_completo['mensagem'].str.contains(padrao_regex, case=False, na=False)].copy()
        
        print(f"Encontradas {len(df_filtrado)} mensagens contendo os termos do dicionário.")

        # 4. Criar a subamostra aleatória a partir dos resultados filtrados
        if len(df_filtrado) > 0:
            n_amostras = min(len(df_filtrado), TAMANHO_AMOSTRA_FINAL)
            
            print(f"Selecionando uma subamostra aleatória de {n_amostras} mensagens para rotulagem...")
            subamostra = df_filtrado.sample(n=n_amostras, random_state=42)
            
            # Adiciona colunas para rotulagem
            subamostra['classificacao_binaria'] = ''
            subamostra['observacoes'] = ''
            
            # Salva o arquivo final
            subamostra.to_csv(ARQUIVO_SAIDA, index=False)
            print(f"Subamostra salva com sucesso em: '{ARQUIVO_SAIDA}'")
        else:
            print("Nenhuma mensagem correspondente foi encontrada. Tente revisar seu dicionário.")

except FileNotFoundError:
    print(f"ERRO: O arquivo '{ARQUIVO_DE_DADOS}' ou '{ARQUIVO_DICIONARIO}' não foi encontrado.")
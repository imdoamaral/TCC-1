# -*- coding: utf-8 -*-
"""
Script para carregar o dataset rotulado, o modelo BERTimbau e seu tokenizador,
e preparar os dados para o treinamento (fine-tuning).
"""

import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification

# --- 1. CONFIGURAÇÕES ---
# Nome do arquivo com os dados rotulados
NOME_ARQUIVO_DADOS = 'amostra_rotulada.csv'

# Nome da coluna que contém os textos dos comentários
NOME_COLUNA_TEXTO = 'mensagem'

# !! IMPORTANTE !!
# Substitua pelo nome exato da coluna que contém os rótulos (0 ou 1)
NOME_COLUNA_ROTULO = 'classificacao_binaria'

# Nome do modelo BERT a ser usado (BERTimbau Cased)
NOME_MODELO_BERT = 'neuralmind/bert-base-portuguese-cased'

# Parâmetros da Tokenização
MAX_LENGTH = 128 # Comprimento máximo das sentenças

# --- 2. FUNÇÃO PRINCIPAL ---
def preparar_dados():
    """
    Função principal que executa todos os passos.
    """
    print("--- INÍCIO DA PREPARAÇÃO DOS DADOS PARA O BERT ---")

    # Carregar o dataset
    try:
        print(f"\n[PASSO 1/4] Carregando o dataset '{NOME_ARQUIVO_DADOS}'...")
        df = pd.read_csv(NOME_ARQUIVO_DADOS)
        print("Dataset carregado com sucesso!")
        print(f"O dataset tem {len(df)} linhas.")
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{NOME_ARQUIVO_DADOS}' não foi encontrado.")
        print("Verifique se o arquivo está na mesma pasta que este script.")
        return

    # Verificar se as colunas necessárias existem
    if NOME_COLUNA_TEXTO not in df.columns or NOME_COLUNA_ROTULO not in df.columns:
        print(f"ERRO: Verifique os nomes das colunas no arquivo de configuração.")
        print(f"Coluna de texto esperada: '{NOME_COLUNA_TEXTO}'")
        print(f"Coluna de rótulo esperada: '{NOME_COLUNA_ROTULO}'")
        print(f"Colunas encontradas no arquivo: {df.columns.tolist()}")
        return

    # Carregar o Tokenizador e o Modelo
    print("\n[PASSO 2/4] Carregando o tokenizador e o modelo BERTimbau...")
    try:
        tokenizer = BertTokenizer.from_pretrained(NOME_MODELO_BERT)
        # Não precisamos carregar o modelo completo aqui, apenas para preparar os dados.
        # Vamos carregá-lo de fato na etapa de treinamento.
        print("Tokenizador carregado com sucesso!")
    except Exception as e:
        print(f"ERRO ao carregar o tokenizador: {e}")
        return

    # Extrair textos e rótulos do DataFrame
    textos = df[NOME_COLUNA_TEXTO].tolist()
    rotulos = df[NOME_COLUNA_ROTULO].tolist()

    # Tokenizar os dados
    print(f"\n[PASSO 3/4] Aplicando o tokenizador em {len(textos)} textos...")
    encoded_data = tokenizer.batch_encode_plus(
        textos,
        add_special_tokens=True,
        return_attention_mask=True,
        padding='max_length',
        max_length=MAX_LENGTH,
        truncation=True,
        return_tensors='pt' # Retorna como Tensores do PyTorch
    )

    input_ids = encoded_data['input_ids']
    attention_masks = encoded_data['attention_mask']
    # Converte a lista de rótulos para o formato de tensor
    labels = torch.tensor(rotulos)

    print("Tokenização completa!")

    # Verificação final
    print("\n[PASSO 4/4] Verificando os resultados...")
    print(f"Formato dos 'input_ids': {input_ids.shape}")
    print(f"Formato das 'attention_masks': {attention_masks.shape}")
    print(f"Formato dos 'labels': {labels.shape}")

    print("\n--- Exemplo da primeira frase processada ---")
    print(f"Texto Original: '{textos[0]}'")
    # O método 'decode' do tokenizador faz o caminho inverso: transforma os IDs de volta em texto
    print(f"Texto decodificado do tensor: '{tokenizer.decode(input_ids[0])}'")
    print(f"Label: {labels[0]}")

    print("\n--- PREPARAÇÃO CONCLUÍDA COM SUCESSO ---")


# --- PONTO DE ENTRADA DO SCRIPT ---
if __name__ == '__main__':
    preparar_dados()
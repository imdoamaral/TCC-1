# -*- coding: utf-8 -*-
"""
Script final para o experimento fatorial com BERT.
Executa N repetições de Bootstrap do treinamento e calcula o F1-Score médio.
Pode ser configurado para rodar com dados 'bruto' ou 'padrao'.
"""
import sys
import time
import datetime
import pandas as pd
import torch
import numpy as np
import re # <--- NOVO: Importar a biblioteca de expressões regulares
from transformers import BertTokenizer, BertForSequenceClassification, AdamW, get_linear_schedule_with_warmup
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
from sklearn.utils import resample

# ... (Classe Logger continua igual) ...
class Logger(object):
    def __init__(self, filename="log.txt"):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding='utf-8')
    def write(self, message):
        self.terminal.write(message); self.log.write(message)
    def flush(self):
        self.terminal.flush(); self.log.flush()


# --- 1. CONFIGURAÇÕES ---
# !! INTERRUPTOR PRINCIPAL !! Altere entre 'bruto' e 'padrao'
TIPO_PREPROCESSAMENTO = 'bruto'  # <--- NOVO: Mude para 'padrao' para o próximo experimento

NOME_ARQUIVO_DADOS = 'amostra_rotulada.csv'
NOME_COLUNA_TEXTO = 'mensagem'
NOME_COLUNA_ROTULO = 'classificacao_binaria'
NOME_MODELO_BERT = 'neuralmind/bert-base-portuguese-cased'
# <--- NOVO: Nome do arquivo de log dinâmico
ARQUIVO_DE_LOG = f'log_experimento_bert_{TIPO_PREPROCESSAMENTO}.txt'
MAX_LENGTH = 128
BATCH_SIZE = 16
TEST_SIZE = 0.15
RANDOM_STATE = 42
EPOCHS = 3
N_REPLICACOES = 30

# <--- NOVO: Função de pré-processamento padrão ---
def preprocessamento_padrao(texto):
    if not isinstance(texto, str): return ""
    texto = texto.lower()
    texto = re.sub(r'[\n\r]+', ' ', texto)
    return texto.strip()
# ... (Função treinar_e_avaliar e outras continuam iguais) ...
def treinar_e_avaliar(df_amostra, device):
    """Recebe uma amostra do dataframe, treina e avalia o modelo, retornando o melhor F1-Score."""
    textos = df_amostra[NOME_COLUNA_TEXTO].astype(str).tolist()
    rotulos = df_amostra[NOME_COLUNA_ROTULO].tolist()

    tokenizer = BertTokenizer.from_pretrained(NOME_MODELO_BERT, do_lower_case=False)
    
    encoded_data = tokenizer.batch_encode_plus(
        textos, add_special_tokens=True, return_attention_mask=True,
        padding='max_length', max_length=MAX_LENGTH, truncation=True, return_tensors='pt'
    )
    input_ids, attention_masks, labels = encoded_data['input_ids'], encoded_data['attention_mask'], torch.tensor(rotulos)

    train_inputs, val_inputs, train_labels, val_labels, train_masks, val_masks = train_test_split(
        input_ids, labels, attention_masks, random_state=RANDOM_STATE,
        test_size=TEST_SIZE, stratify=labels
    )

    train_data = TensorDataset(train_inputs, train_masks, train_labels)
    train_sampler = RandomSampler(train_data)
    train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=BATCH_SIZE)

    val_data = TensorDataset(val_inputs, val_masks, val_labels)
    val_sampler = SequentialSampler(val_data)
    val_dataloader = DataLoader(val_data, sampler=val_sampler, batch_size=BATCH_SIZE)

    model = BertForSequenceClassification.from_pretrained(
        NOME_MODELO_BERT, num_labels=2, output_attentions=False, output_hidden_states=False,
    )
    model.to(device)

    optimizer = AdamW(model.parameters(), lr=2e-5, eps=1e-8)
    total_steps = len(train_dataloader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)
    
    best_f1_score = 0.0

    for epoch_i in range(0, EPOCHS):
        model.train()
        for batch in train_dataloader:
            b_input_ids, b_input_mask, b_labels = batch[0].to(device), batch[1].to(device), batch[2].to(device)
            model.zero_grad()
            output = model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask, labels=b_labels)
            loss = output.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

        model.eval()
        all_preds, all_labels = [], []
        for batch in val_dataloader:
            b_input_ids, b_input_mask, b_labels = batch[0].to(device), batch[1].to(device), batch[2].to(device)
            with torch.no_grad():
                output = model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask)
            logits = output.logits
            preds = np.argmax(logits.detach().cpu().numpy(), axis=1).flatten()
            labels = b_labels.cpu().numpy().flatten()
            all_preds.extend(preds); all_labels.extend(labels)
            
        f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
        if f1 > best_f1_score:
            best_f1_score = f1
            
    return best_f1_score

# --- 3. FUNÇÃO PRINCIPAL DO SCRIPT ---
def main():
    df_original = pd.read_csv(NOME_ARQUIVO_DADOS)
    
    # <--- NOVO: Aplica o pré-processamento de acordo com o interruptor ---
    print(f"Modo de pré-processamento selecionado: '{TIPO_PREPROCESSAMENTO}'")
    if TIPO_PREPROCESSAMENTO == 'padrao':
        print("Aplicando pré-processamento padrão na coluna de mensagens...")
        df_original[NOME_COLUNA_TEXTO] = df_original[NOME_COLUNA_TEXTO].apply(preprocessamento_padrao)
        print("Pré-processamento aplicado com sucesso.\n")
    
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f'Usando GPU: {torch.cuda.get_device_name(0)}\n')
    else:
        device = torch.device("cpu")
        print('Nenhuma GPU encontrada, usando CPU.\n')

    # ... (Restante da função main continua igual) ...
    lista_de_f1_scores = []
    
    print(f"--- Iniciando {N_REPLICACOES} repetições de Bootstrap ---")
    
    for i in range(N_REPLICACOES):
        t0 = time.time()
        print(f"\n--- Repetição {i + 1}/{N_REPLICACOES} ---")
        
        # Gera a amostra de bootstrap
        amostra_bootstrap = resample(df_original, replace=True, n_samples=len(df_original), random_state=i)
        
        # Treina e avalia na amostra, obtendo o melhor F1
        melhor_f1 = treinar_e_avaliar(amostra_bootstrap, device)
        lista_de_f1_scores.append(melhor_f1)
        
        tempo_da_replica = time.strftime("%H:%M:%S", time.gmtime(time.time() - t0))
        print(f"Melhor F1-Score da repetição: {melhor_f1:.4f}")
        print(f"Tempo da repetição: {tempo_da_replica}")

    # --- Resultados Finais ---
    f1_medio = np.mean(lista_de_f1_scores)
    f1_std = np.std(lista_de_f1_scores)
    
    print("\n" + "="*50)
    print("---            RESULTADO FINAL DO EXPERIMENTO            ---")
    print("="*50)
    print(f"Modelo: {NOME_MODELO_BERT}")
    print(f"Pré-processamento: {TIPO_PREPROCESSAMENTO}")
    print(f"Número de Replicações: {N_REPLICACOES}")
    print(f"F1-Scores individuais: {lista_de_f1_scores}")
    print("\n" + "-"*50)
    print(f"F1-SCORE MÉDIO (MACRO): {f1_medio:.4f}")
    print(f"Desvio Padrão dos F1-Scores: {f1_std:.4f}")
    print("="*50)

if __name__ == '__main__':
    sys.stdout = Logger(ARQUIVO_DE_LOG)
    print(f"Iniciando execução do script: {datetime.datetime.now()}")
    print("-" * 30)
    main()
    print("-" * 30)
    print(f"Execução finalizada: {datetime.datetime.now()}")
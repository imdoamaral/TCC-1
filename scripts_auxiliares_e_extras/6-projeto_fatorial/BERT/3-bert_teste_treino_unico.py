# -*- coding: utf-8 -*-
"""
Script principal para o experimento com BERT.
Passos:
1. Carrega e tokeniza os dados.
2. Divide os dados em conjuntos de treino e validação.
3. Cria DataLoaders para alimentar o modelo de forma eficiente.
4. Define e executa o loop de treinamento e validação.
5. Salva toda a saída em um arquivo de log.
"""
import sys
import time
import datetime
import pandas as pd
import torch
import numpy as np
from torch.optim import AdamW
from transformers import BertTokenizer, BertForSequenceClassification, get_linear_schedule_with_warmup
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

# --- CLASSE PARA GERAR O LOG ---
class Logger(object):
    def __init__(self, filename="log.txt"):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # O flush é necessário para alguns ambientes de execução
        self.terminal.flush()
        self.log.flush()

# --- 1. CONFIGURAÇÕES ---
NOME_ARQUIVO_DADOS = 'amostra_rotulada.csv'
NOME_COLUNA_TEXTO = 'mensagem'
NOME_COLUNA_ROTULO = 'classificacao_binaria'
NOME_MODELO_BERT = 'neuralmind/bert-base-portuguese-cased'
ARQUIVO_DE_LOG = 'log_treinamento_bert.txt'
MAX_LENGTH = 128
BATCH_SIZE = 16
TEST_SIZE = 0.15
RANDOM_STATE = 42
EPOCHS = 3

# --- 2. FUNÇÕES AUXILIARES ---
def format_time(elapsed):
    elapsed_rounded = int(round((elapsed)))
    return str(datetime.timedelta(seconds=elapsed_rounded))

# --- 3. FUNÇÃO PARA CARREGAR E PREPARAR OS DADOS ---
def preparar_e_organizar_dados():
    # ... (O restante das funções continua exatamente igual)
    print("--- FASE 1: Carregando, preparando e organizando os dados ---")
    df = pd.read_csv(NOME_ARQUIVO_DADOS)
    textos = df[NOME_COLUNA_TEXTO].astype(str).tolist()
    rotulos = df[NOME_COLUNA_ROTULO].tolist()

    tokenizer = BertTokenizer.from_pretrained(NOME_MODELO_BERT)

    encoded_data = tokenizer.batch_encode_plus(
        textos, add_special_tokens=True, return_attention_mask=True,
        padding='max_length', max_length=MAX_LENGTH, truncation=True, return_tensors='pt'
    )

    input_ids = encoded_data['input_ids']
    attention_masks = encoded_data['attention_mask']
    labels = torch.tensor(rotulos)

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

    print("Dados prontos e organizados em DataLoaders.\n")
    return train_dataloader, val_dataloader

# --- 4. FUNÇÃO PRINCIPAL DO SCRIPT ---
def main():
    train_dataloader, val_dataloader = preparar_e_organizar_dados()

    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f'Usando GPU: {torch.cuda.get_device_name(0)}\n')
    else:
        device = torch.device("cpu")
        print('Nenhuma GPU encontrada, usando CPU.\n')

    model = BertForSequenceClassification.from_pretrained(
        NOME_MODELO_BERT, num_labels=2, output_attentions=False, output_hidden_states=False,
    )
    model.to(device)

    optimizer = AdamW(model.parameters(), lr=2e-5, eps=1e-8)
    total_steps = len(train_dataloader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)

    print(f"--- FASE 2: Iniciando o treinamento por {EPOCHS} épocas ---")
    
    for epoch_i in range(0, EPOCHS):
        print(f'\n======== Época {epoch_i + 1} / {EPOCHS} ========')
        print('Treinando...')
        t0 = time.time()
        total_train_loss = 0
        model.train()

        for step, batch in enumerate(train_dataloader):
            if step % 40 == 0 and not step == 0:
                elapsed = format_time(time.time() - t0)
                print(f'  Lote {step:>5} de {len(train_dataloader):>5}. Tempo: {elapsed}.')

            b_input_ids, b_input_mask, b_labels = batch[0].to(device), batch[1].to(device), batch[2].to(device)
            model.zero_grad()
            output = model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask, labels=b_labels)
            loss = output.loss
            total_train_loss += loss.item()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

        avg_train_loss = total_train_loss / len(train_dataloader)
        training_time = format_time(time.time() - t0)
        print(f"\n  Média da perda de treino: {avg_train_loss:.4f}")
        print(f"  Tempo de treino da época: {training_time}")

        print("\nValidando...")
        t0 = time.time()
        model.eval()
        all_preds, all_labels = [], []

        for batch in val_dataloader:
            b_input_ids, b_input_mask, b_labels = batch[0].to(device), batch[1].to(device), batch[2].to(device)
            with torch.no_grad():
                output = model(b_input_ids, token_type_ids=None, attention_mask=b_input_mask)
            
            logits = output.logits
            preds = np.argmax(logits.detach().cpu().numpy(), axis=1).flatten()
            labels = b_labels.cpu().numpy().flatten()
            all_preds.extend(preds)
            all_labels.extend(labels)
            
        f1 = f1_score(all_labels, all_preds, average='macro')
        print(f"  F1-Score (Macro) na validação: {f1:.4f}")
        validation_time = format_time(time.time() - t0)
        print(f"  Tempo de validação: {validation_time}")

    print("\n--- Treinamento Concluído! ---")

if __name__ == '__main__':
    # Redireciona a saída padrão (stdout) para o nosso logger
    sys.stdout = Logger(ARQUIVO_DE_LOG)
    
    print("Iniciando execução do script...")
    print(f"Data e Hora: {datetime.datetime.now()}")
    print("-" * 30)
    
    main() # Executa a função principal
    
    print("-" * 30)
    print("Execução finalizada.")
import pandas as pd
import numpy as np
import re
import time
from sklearn.metrics import f1_score, confusion_matrix
from tqdm import tqdm
from googleapiclient import discovery
from googleapiclient.errors import HttpError

# --- PARÂMETROS DO EXPERIMENTO ---
API_KEY = "INSERIR_CHAVE_API_AQUI"
ARQUIVO_ROTULADO = "amostra_rotulada.csv"
ARQUIVO_LOG = "log_experimento.txt"
N_REPLICACOES = 30
LIMIAR_TOXICIDADE = 0.60

# --- INÍCIO DO LOG ---
log_output = []
log_output.append("--- INÍCIO DO LOG DO EXPERIMENTO ---")
log_output.append(f"Data de execução: {pd.Timestamp.now()}")
log_output.append("-" * 30)

# --- FUNÇÕES ---

def preprocessamento_padrao(texto):
    if not isinstance(texto, str): return ""
    texto = texto.lower()
    texto = re.sub(r'[\n\r]+', ' ', texto)
    return texto.strip()

def obter_predicoes_api(dataframe, api_key):
    client = discovery.build("commentanalyzer", "v1alpha1", developerKey=api_key, static_discovery=False)
    textos = dataframe['mensagem_processada'].tolist()
    predicoes = []
    scores = []

    print(f"Iniciando {len(textos)} chamadas à Perspective API...")
    log_output.append(f"\nIniciando {len(textos)} chamadas à Perspective API...")
    for texto in tqdm(textos, desc="Consultando API"):
        if not texto:
            predicoes.append(0)
            scores.append(0.0)
            continue

        analyze_request = {'comment': {'text': texto}, 'requestedAttributes': {'TOXICITY': {}}, 'languages': ['pt']}
        
        try:
            response = client.comments().analyze(body=analyze_request).execute()
            score = response['attributeScores']['TOXICITY']['summaryScore']['value']
            predicao = 1 if score > LIMIAR_TOXICIDADE else 0
            predicoes.append(predicao)
            scores.append(score)
        except HttpError as e:
            error_msg = f"Erro na API para o texto: '{texto[:30]}...'. Erro: {e}. Assumindo predição 'Não Tóxico'."
            print(error_msg)
            log_output.append(error_msg)
            predicoes.append(0)
            scores.append(-1.0)

        time.sleep(1.1)
    
    return predicoes, scores

def analisar_debug(df_com_predicoes, nome_cenario):
    log_debug = []
    log_debug.append(f"\n--- ANÁLISE DE DEBUG ({nome_cenario}) ---")
    
    df_debug = df_com_predicoes[(df_com_predicoes['classificacao_binaria'] == 1) | (df_com_predicoes['predicao_api'] == 1)].copy()

    if df_debug.empty:
        log_debug.append("DEBUG: Nenhum comentário tóxico foi encontrado na amostra E a API não previu nenhum como tóxico.")
    else:
        log_debug.append("Casos relevantes (Reais=1 ou Preditos=1):")
        log_debug.append(df_debug[['mensagem', 'classificacao_binaria', 'score_api', 'predicao_api']].to_string())

    log_debug.append("\nMatriz de Confusão:")
    cm = confusion_matrix(df_com_predicoes['classificacao_binaria'], df_com_predicoes['predicao_api'], labels=[0, 1])
    df_cm = pd.DataFrame(cm, index=['Real: Não Tóxico', 'Real: Tóxico'], columns=['Predito: Não Tóxico', 'Predito: Tóxico'])
    log_debug.append(df_cm.to_string())
    log_debug.append("-" * 25)
    
    # Imprime na tela e retorna a string para o log principal
    full_log_string = "\n".join(log_debug)
    print(full_log_string)
    return full_log_string

# --- EXECUÇÃO DO EXPERIMENTO ---

print("Carregando dados rotulados...")
df_original = pd.read_csv(ARQUIVO_ROTULADO)

# # --- MODO DE TESTE (comente ou remova para ativar/desativar) ---
# df_original = df_original.sample(n=50, random_state=42)
# msg_teste = f"--- ATENÇÃO: RODANDO EM MODO DE TESTE COM APENAS {len(df_original)} AMOSTRAS ---"
# print(msg_teste)
# log_output.append(msg_teste)
# # -----------------------------------------

df_original['mensagem'] = df_original['mensagem'].astype(str)

# Prepara os dataframes
df_bruto = df_original.copy()
df_bruto['mensagem_processada'] = df_bruto['mensagem']
df_padrao = df_original.copy()
df_padrao['mensagem_processada'] = df_padrao['mensagem'].apply(preprocessamento_padrao)

# Obtém as predições e scores
df_bruto['predicao_api'], df_bruto['score_api'] = obter_predicoes_api(df_bruto, API_KEY)
df_padrao['predicao_api'], df_padrao['score_api'] = obter_predicoes_api(df_padrao, API_KEY)

# Roda e salva a análise de debug
log_output.append(analisar_debug(df_bruto, "Bruto"))
log_output.append(analisar_debug(df_padrao, "Padrão"))

# Realiza o Bootstrap
resultados = {"bruto": [], "padrao": []}
print("\n--- Iniciando simulação Bootstrap (rápido) ---")
for df, nome_cenario in [(df_bruto, "bruto"), (df_padrao, "padrao")]:
    for i in tqdm(range(N_REPLICACOES), desc=f"Bootstrap ({nome_cenario.capitalize()})"):
        amostra = df.sample(n=len(df), replace=True, random_state=i)
        f1 = f1_score(amostra['classificacao_binaria'], amostra['predicao_api'], pos_label=1, zero_division=0)
        resultados[nome_cenario].append(f1)

# --- ANÁLISE E LOG DOS RESULTADOS FINAIS ---

media_bruto = np.mean(resultados["bruto"])
std_bruto = np.std(resultados["bruto"])
media_padrao = np.mean(resultados["padrao"])
std_padrao = np.std(resultados["padrao"])

# Prepara as strings para o log e para a impressão na tela
header_final = "\n\n--- Resultados Finais do Experimento (Perspective API) ---"
resultado_bruto_str = f"Pré-processamento Bruto:      F1-Score Médio = {media_bruto:.4f} (Desvio Padrão = {std_bruto:.4f})"
resultado_padrao_str = f"Pré-processamento Padrão:     F1-Score Médio = {media_padrao:.4f} (Desvio Padrão = {std_padrao:.4f})"
header_y = "\nEstes são os valores de 'y' (variável resposta) para sua análise fatorial:"
y_bruto_str = f"y (nível -1, Bruto) = {media_bruto:.4f}"
y_padrao_str = f"y (nível +1, Padrão) = {media_padrao:.4f}"

# Imprime na tela
print(header_final)
print(resultado_bruto_str)
print(resultado_padrao_str)
print(header_y)
print(y_bruto_str)
print(y_padrao_str)

# Adiciona ao log
log_output.append(header_final)
log_output.append(resultado_bruto_str)
log_output.append(resultado_padrao_str)
log_output.append(header_y)
log_output.append(y_bruto_str)
log_output.append(y_padrao_str)

# --- SALVA O ARQUIVO DE LOG ---
log_output.append("\n--- FIM DO LOG ---")
try:
    with open(ARQUIVO_LOG, 'w', encoding='utf-8') as f:
        f.write("\n".join(log_output))
    print(f"\nLog completo do experimento salvo em: '{ARQUIVO_LOG}'")
except Exception as e:
    print(f"\nERRO ao salvar o arquivo de log: {e}")
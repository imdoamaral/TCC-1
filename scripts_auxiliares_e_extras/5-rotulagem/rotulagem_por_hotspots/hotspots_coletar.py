import pandas as pd

# --- PARÂMETROS DE CONFIGURAÇÃO ---
ARQUIVO_DE_DADOS = "dataset_unificado.csv"
ARQUIVO_HOTSPOTS = "hotspots_encontrados.csv" # <-- MUDANÇA AQUI
JANELA_COLETA_MINUTOS = 1
ARQUIVO_SAIDA = "amostra_hotspots_para_rotular.csv"
# --- FIM DA CONFIGURAÇÃO ---


# --- INÍCIO DO SCRIPT ---

# 1. Carregar os dados do dataset completo
print(f"Carregando dataset completo: {ARQUIVO_DE_DADOS}...")
df_completo = pd.read_csv(ARQUIVO_DE_DADOS)
df_completo['timestamp'] = pd.to_datetime(df_completo['timestamp'])

# 2. Carregar o arquivo de hotspots gerado pelo script anterior
print(f"Carregando arquivo de hotspots: {ARQUIVO_HOTSPOTS}...")
hotspots_df = pd.read_csv(ARQUIVO_HOTSPOTS)
hotspots_df['timestamp_hotspot'] = pd.to_datetime(hotspots_df['timestamp_hotspot'])

# 3. Identificar os eventos únicos para não coletar dados repetidos
eventos_unicos = hotspots_df.sort_values('mensagens_na_janela', ascending=False).drop_duplicates(subset=['id_video', 'titulo_live'])
print(f"\nIdentificados {len(eventos_unicos)} eventos únicos de alta densidade para investigar.")

# Lista para guardar todas as mensagens coletadas
mensagens_coletadas = []

# 4. Loop através de cada evento para coletar as mensagens
for index, evento in eventos_unicos.iterrows():
    video_id = evento['id_video']
    ponto_central = evento['timestamp_hotspot']
    
    inicio_janela = ponto_central - pd.Timedelta(minutes=JANELA_COLETA_MINUTOS)
    fim_janela = ponto_central + pd.Timedelta(minutes=JANELA_COLETA_MINUTOS)
    
    print(f"Coletando mensagens para o vídeo '{video_id}' entre {inicio_janela.time()} e {fim_janela.time()}...")
    
    mensagens_do_hotspot = df_completo[
        (df_completo['id_video'] == video_id) &
        (df_completo['timestamp'] >= inicio_janela) &
        (df_completo['timestamp'] <= fim_janela)
    ]
    
    mensagens_coletadas.append(mensagens_do_hotspot)

# 5. Juntar tudo em um único dataframe e salvar
if mensagens_coletadas:
    df_final = pd.concat(mensagens_coletadas).drop_duplicates().reset_index(drop=True)
    df_final.sort_values(by=['id_video', 'timestamp'], inplace=True)
    
    print(f"\nColeta finalizada! Total de {len(df_final)} mensagens coletadas dos hotspots.")
    
    df_final['classificacao_binaria'] = ''
    df_final['observacoes'] = ''
    
    df_final.to_csv(ARQUIVO_SAIDA, index=False)
    print(f"Nova amostra salva em: '{ARQUIVO_SAIDA}'")
else:
    print("\nNenhuma mensagem foi coletada.")
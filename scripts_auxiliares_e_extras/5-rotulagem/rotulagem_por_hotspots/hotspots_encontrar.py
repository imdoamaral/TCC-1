import pandas as pd

# --- PARÂMETROS DE CONFIGURAÇÃO ---
ARQUIVO_DE_DADOS = "dataset_unificado.csv"
CANAIS_ALVO = ["LUANGAMEPLAY", "REnanPLAY"]
TAMANHO_JANELA = "10s"
TOP_N_HOTSPOTS = 10
# --- FIM DA CONFIGURAÇÃO ---


def encontrar_hotspots(df):
    print("Iniciando a análise de densidade de mensagens...")
    print("Convertendo coluna de timestamp...")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values(by=['id_video', 'timestamp'], inplace=True)
    
    todos_os_hotspots = []
    videos_unicos = df[df['canal'].isin(CANAIS_ALVO)]['id_video'].unique()
    print(f"Encontrados {len(videos_unicos)} vídeos para os canais {CANAIS_ALVO}.")

    for video_id in videos_unicos:
        live_df = df[df['id_video'] == video_id].copy()
        canal_nome = live_df['canal'].iloc[0]
        titulo_live = live_df['titulo'].iloc[0]
        print(f"\nAnalisando live: '{titulo_live}' ({canal_nome})...")
        live_df.set_index('timestamp', inplace=True)
        live_df['contagem'] = 1
        densidade = live_df['contagem'].rolling(window=TAMANHO_JANELA).sum()
        top_hotspots = densidade.nlargest(TOP_N_HOTSPOTS)

        for timestamp_hotspot, contagem_msg in top_hotspots.items():
            todos_os_hotspots.append({
                "canal": canal_nome,
                "titulo_live": titulo_live,
                "timestamp_hotspot": timestamp_hotspot,
                "mensagens_na_janela": int(contagem_msg),
                "id_video": video_id
            })
    
    return pd.DataFrame(todos_os_hotspots)

# --- EXECUÇÃO DO SCRIPT ---
if __name__ == "__main__":
    try:
        df_completo = pd.read_csv(ARQUIVO_DE_DADOS)
        hotspots_df = encontrar_hotspots(df_completo)
        
        print("\n\n--- RESULTADO FINAL: TOP HOTSPOTS ENCONTRADOS ---")
        if not hotspots_df.empty:
            hotspots_df.sort_values(by='mensagens_na_janela', ascending=False, inplace=True)
            print(hotspots_df.to_string())
            
            # --- LINHA ADICIONADA ---
            # Salva o resultado em um arquivo CSV para o próximo script usar
            hotspots_df.to_csv("hotspots_encontrados.csv", index=False)
            print("\nArquivo 'hotspots_encontrados.csv' salvo com sucesso!")
            
        else:
            print("Nenhum hotspot encontrado para os canais especificados.")
            
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{ARQUIVO_DE_DADOS}' não foi encontrado.")
    except KeyError as e:
        print(f"ERRO: Uma coluna necessária não foi encontrada no arquivo: {e}")
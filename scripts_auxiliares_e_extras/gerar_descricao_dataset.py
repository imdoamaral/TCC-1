import pandas as pd
import pytz

# Carrega o dataset
df = pd.read_csv("dataset_unificado.csv")

# Converte timestamp para datetime usando formato misto
df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', utc=True)
tz_local = pytz.timezone('America/Sao_Paulo')
df['timestamp_local'] = df['timestamp'].dt.tz_convert(tz_local)

# Calcula o número total de mensagens
total_mensagens = len(df)

# Número de lives por canal (contagem única de id_video por canal)
lives_por_canal = df.groupby('canal')['id_video'].nunique().reset_index(name='Live Count')

# Período de coleta (data mínima e máxima)
periodo_inicio = df['timestamp_local'].min().strftime('%d/%m/%Y %H:%M')
periodo_fim = df['timestamp_local'].max().strftime('%d/%m/%Y %H:%M')

# Cria uma tabela com informações agregadas
tabela = pd.DataFrame({
    'Canal': lives_por_canal['canal'],
    'Live Count': lives_por_canal['Live Count'],
    'Total Mensagens': df.groupby('canal').size().reindex(lives_por_canal['canal']).values,
})

# Exibe a tabela
print("Tabela de Informações por Canal:")
print(tabela)

# Descrição do Dataset
descricao = f"""
Dataset Description:
- Canais analisados: {len(lives_por_canal)}
- Período: {periodo_inicio} a {periodo_fim}
- Total de mensagens: {total_mensagens}
- Total de lives: {lives_por_canal['Live Count'].sum()}
"""
print(descricao)
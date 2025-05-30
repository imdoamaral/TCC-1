import pandas as pd
import os
import re

# --- CONFIGURAÇÃO ---
canais = [
    'renanplay',
    'luangameplay',
    'cavalao2',
    'biahkov',
    'fabiojunior',
    'diegosheipado',
    'canaldoronaldinho',
    'wallacegamer'
]

# Quantidade de inscritos fixa
inscritos_fixo = {
    'renanplay': 150_000,
    'luangameplay': 1_440_000,
    'cavalao2': 7_410,
    'biahkov': 31_700,
    'fabiojunior': 23_900,
    'diegosheipado': 37_300,
    'canaldoronaldinho': 98_600,
    'wallacegamer': 685
}

pasta_csv = 'TCC_1/scripts_auxiliares_e_extras/lives_gravadas_streamers'
resumo = []

def parse_views(val):
    if pd.isna(val):
        return 0
    s = str(val)
    s = re.sub(r'[^\d]', '', s)
    return int(s) if s else 0

for canal in canais:
    arquivo = os.path.join(pasta_csv, f'lives_{canal}_2025.csv')
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
        if 'Visualizações' not in df.columns:
            vis_col = [c for c in df.columns if 'isual' in c.lower()]
            if vis_col:
                df.rename(columns={vis_col[0]: 'Visualizações'}, inplace=True)
            else:
                df['Visualizações'] = 0
        df['Visualizações'] = df['Visualizações'].apply(parse_views)
        total_lives = len(df)
        total_views_2025 = df['Visualizações'].sum()
        resumo.append({
            'Canal': canal,
            'Views 2025': total_views_2025,
            'Lives 2025': total_lives,
            'Inscritos': inscritos_fixo.get(canal, 0)
        })
    else:
        resumo.append({
            'Canal': canal,
            'Views 2025': 0,
            'Lives 2025': 0,
            'Inscritos': inscritos_fixo.get(canal, 0)
        })

df_resumo = pd.DataFrame(resumo)
df_resumo = df_resumo.sort_values(by='Views 2025', ascending=False).reset_index(drop=True)

def formatar_int(n):
    try:
        n = int(float(n))
        return f"{n:,}".replace(",", ".")
    except Exception:
        return str(n)

for col in ['Views 2025', 'Lives 2025', 'Inscritos']:
    if col in df_resumo.columns:
        df_resumo[col] = df_resumo[col].apply(formatar_int)

# --- EXPORTAR CSV ---
df_resumo.to_csv("relatorio_lives_calvoesfera_2025.csv", index=False)

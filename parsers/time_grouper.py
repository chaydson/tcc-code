import os
import pandas as pd
import subprocess
import glob
from datetime import timedelta

def generate_commit_timeline_anchored(
    merges_path="../raw-data/merges", 
    repo_path="../../decidim-govbr-lappis",
    output_file="merge_timeline.csv"
):
    """
    Busca as datas dos commits e os agrupa em quinzenas (14 dias),
    usando como âncora fixa o período que inicia em 09/11/2025.
    """
    
    ANCHOR_DATE = pd.Timestamp("2025-11-09", tz="UTC")
    
    search_pattern = os.path.join(merges_path, "*")
    dirs = glob.glob(search_pattern)
    commit_hashes = [os.path.basename(d) for d in dirs if os.path.isdir(d)]

    if not commit_hashes:
        print("Nenhum diretório de hash encontrado.")
        return

    print(f"Encontrados {len(commit_hashes)} hashes. Buscando datas no git...")
    data_list = []

    for commit_hash in commit_hashes:
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%ci", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            date_str = result.stdout.strip()
            data_list.append({"commit_hash": commit_hash, "date": date_str})
        except Exception as e:
            print(f"Erro no hash {commit_hash}: {e}")

    if not data_list:
        return

    df = pd.DataFrame(data_list)
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['days_diff'] = (df['date'] - ANCHOR_DATE).dt.days
    df['group_offset'] = df['days_diff'] // 14

    def calculate_period_label(offset):
        period_start = ANCHOR_DATE + timedelta(days=offset * 14)
        period_end = period_start + timedelta(days=13)
        return f"{period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"

    df['period_label'] = df['group_offset'].apply(calculate_period_label)
    df = df.sort_values(by='date')

    min_offset = df['group_offset'].min()
    df['sequential_id'] = df['group_offset'] - min_offset + 1

    print("\n--- Amostra do Agrupamento (Baseado em 09/11/2025) ---")
    print(df[['commit_hash', 'date', 'group_offset', 'period_label']].tail(10))
    
    print(f"\nO grupo '0' corresponde ao período alvo: 2025-11-09 a 2025-11-22")
    print(f"Grupos negativos (-1, -2...) são quinzenas anteriores.")

    df.to_csv(output_file, index=False)
    print(f"\nArquivo '{output_file}' salvo com sucesso.")

if __name__ == "__main__":
    generate_commit_timeline_anchored(
        merges_path="../raw-data/merges",
        repo_path="../../decidim-govbr-lappis" 
    )
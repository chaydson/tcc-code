import pandas as pd
import json
import glob
import os

def analyze_merges_brakeman(base_path="../raw-data/merges"):
    """
    Percorre a pasta de merges, lê os relatórios do Brakeman
    e gera um DataFrame consolidado com as contagens por nível de confiança.
    """
    search_pattern = os.path.join(base_path, "*", "artifacts", "brakeman-report.json")
    files = glob.glob(search_pattern)

    if not files:
        print(f"Nenhum arquivo encontrado no padrão: {search_pattern}")
        return

    results = []

    print(f"Encontrados {len(files)} relatórios. Processando...")

    for filepath in files:
        try:
            path_parts = os.path.normpath(filepath).split(os.sep)
            commit_hash = path_parts[-3]

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            warnings_list = data.get("warnings", [])
            
            row = {'commit_hash': commit_hash}

            if warnings_list:
                df_temp = pd.DataFrame(warnings_list)
                
                if "confidence" in df_temp.columns:
                    counts = df_temp['confidence'].value_counts().to_dict()
                    row.update(counts)
                else:
                    print(f"Aviso: Coluna 'confidence' não encontrada em {commit_hash}")
            
            row['total_scan_info'] = data.get("scan_info", {}).get("security_warnings", 0)
            
            results.append(row)

        except Exception as e:
            print(f"Erro ao processar {filepath}: {e}")

    if results:
        df_final = pd.DataFrame(results)
        df_final = df_final.fillna(0)

        cols = ['commit_hash', 'High', 'Medium', 'Weak', 'total_scan_info']
        cols = [c for c in cols if c in df_final.columns] 
        remaining_cols = [c for c in df_final.columns if c not in cols]
        df_final = df_final[cols + remaining_cols]

        print("\n--- Resumo dos Merges Processados ---")
        print(df_final.to_string(index=False))
        return df_final
        
    else:
        print("Nenhum resultado foi extraído dos arquivos.")
        return pd.DataFrame()

if __name__ == "__main__":
    analyze_merges_brakeman(base_path="../raw-data/merges")
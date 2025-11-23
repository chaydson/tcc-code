import pandas as pd
import json
import glob
import os

def analyze_merges_zap(base_path="../raw-data/merges"):
    """
    Percorre a pasta de merges, lê os relatórios do OWASP ZAP 
    (geralmente baseline-report.json), agrupa por nível de risco 
    e soma as instâncias (count).
    """
    
    search_pattern = os.path.join(base_path, "*", "artifacts", "zap-report.json")
    files = glob.glob(search_pattern)

    if not files:
        print(f"Nenhum arquivo encontrado no padrão: {search_pattern}")
        return

    results = []

    print(f"Encontrados {len(files)} relatórios do ZAP. Processando...")

    for filepath in files:
        try:
            path_parts = os.path.normpath(filepath).split(os.sep)
            commit_hash = path_parts[-3]

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            site_data = data.get("site", [{}])[0]
            alerts_list = site_data.get("alerts", [])

            row = {'commit_hash': commit_hash}
            total_instances = 0

            if alerts_list:
                df_temp = pd.DataFrame(alerts_list)

                risk_map = {
                    "3": "High",
                    "2": "Medium",
                    "1": "Low",
                    "0": "Informational"
                }

                df_temp['Risk Level'] = df_temp['riskcode'].apply(lambda x: risk_map.get(x, f"Unknown ({x})"))
                
                df_temp['count'] = pd.to_numeric(df_temp['count'], errors='coerce').fillna(0)

                grouped = df_temp.groupby('Risk Level')['count'].sum()
                
                row.update(grouped.to_dict())
                
                total_instances = grouped.sum()
            
            row['total_instances'] = total_instances
            results.append(row)

        except Exception as e:
            print(f"Erro ao processar {filepath}: {e}")

    if results:
        df_final = pd.DataFrame(results)
    
        df_final = df_final.fillna(0)
        ordered_levels = ["High", "Medium", "Low", "Informational"]
        cols_to_show = [col for col in ordered_levels if col in df_final.columns]
        final_cols = ['commit_hash'] + cols_to_show + ['total_instances']
        remaining = [c for c in df_final.columns if c not in final_cols]
        df_final = df_final[final_cols + remaining]

        print("\n--- Resumo dos Merges Processados (ZAP) ---")
        print(df_final.to_string(index=False))

        return df_final

    else:
        print("Nenhum resultado foi extraído dos arquivos.")
        return pd.DataFrame()

if __name__ == "__main__":
    analyze_merges_zap()
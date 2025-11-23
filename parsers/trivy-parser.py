import pandas as pd
import json
import glob
import os

def analyze_merges_trivy(base_path="../raw-data/merges"):
    """
    Percorre a pasta de merges, lê os relatórios do Trivy (que podem conter
    vulnerabilidades e segredos) e gera um DataFrame consolidado com as 
    contagens por severidade.
    """
    
    search_pattern = os.path.join(base_path, "*", "artifacts", "trivy-report.json")
    files = glob.glob(search_pattern)

    if not files:
        print(f"Nenhum arquivo encontrado no padrão: {search_pattern}")
        return

    results = []

    print(f"Encontrados {len(files)} relatórios do Trivy. Processando...")

    for filepath in files:
        try:
            path_parts = os.path.normpath(filepath).split(os.sep)
            commit_hash = path_parts[-3]

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            trivy_results = data.get("Results", [])
            
            commit_severities = []
            
            for result in trivy_results:
                for vuln in result.get("Vulnerabilities", []):
                    commit_severities.append(vuln.get("Severity"))
                
                for secret in result.get("Secrets", []):
                    commit_severities.append(secret.get("Severity"))

            row = {'commit_hash': commit_hash}

            if commit_severities:
                counts = pd.Series(commit_severities).value_counts().to_dict()
                row.update(counts)
                row['total_findings'] = len(commit_severities)
            else:
                row['total_findings'] = 0

            results.append(row)

        except Exception as e:
            print(f"Erro ao processar {filepath}: {e}")

    if results:
        df_final = pd.DataFrame(results)
        
        df_final = df_final.fillna(0)

        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']
        
        existing_severities = [col for col in severity_order if col in df_final.columns]
        
        final_cols = ['commit_hash'] + existing_severities + ['total_findings']
        remaining_cols = [c for c in df_final.columns if c not in final_cols]
        
        df_final = df_final[final_cols + remaining_cols]

        print("\n--- Resumo dos Merges Processados (Trivy) ---")
        print(df_final.to_string(index=False))
        return df_final

    else:
        print("Nenhum resultado foi extraído dos arquivos.")
        return pd.DataFrame()

if __name__ == "__main__":
    analyze_merges_trivy()
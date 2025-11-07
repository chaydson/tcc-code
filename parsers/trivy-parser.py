import pandas as pd
import json

def analyze_trivy_json_report(filename="../raw-data/baseline/trivy-reports/trivy-report.json"):
    """
    Analisa um relatório JSON do Trivy usando Pandas, extrai
    vulnerabilidades e segredos, e os conta por nível de severidade.
    """
    print(f"--- Analisando o relatório '{filename}' ---")
    
    try:
        # Abre e carrega o arquivo JSON
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        all_findings = []
        
        # Extrai a lista de "Results"
        results = data.get("Results", [])

        if not results:
            print("Nenhum resultado (Results) encontrado no relatório.")
            return

        # Itera sobre cada "Target" (ex: Gemfile.lock, yarn.lock, etc.)
        for result in results:
            # Extrai vulnerabilidades de dependências
            vulnerabilities = result.get("Vulnerabilities", [])
            for vuln in vulnerabilities:
                all_findings.append({
                    "Target": result.get("Target"),
                    "Type": "Vulnerability",
                    "ID": vuln.get("VulnerabilityID"),
                    "Package": vuln.get("PkgName"),
                    "Severity": vuln.get("Severity")
                })

            # Extrai segredos encontrados
            secrets = result.get("Secrets", [])
            for secret in secrets:
                 all_findings.append({
                    "Target": result.get("Target"),
                    "Type": "Secret",
                    "ID": secret.get("RuleID"),
                    "Package": "N/A", # Segredos não têm pacotes
                    "Severity": secret.get("Severity")
                })

        if not all_findings:
            print("Nenhuma vulnerabilidade ou segredo encontrado nos resultados.")
            return

        # Carrega todas as descobertas em um DataFrame do Pandas
        df = pd.DataFrame(all_findings)

        # Verifica se a coluna 'Severity' existe
        if "Severity" not in df.columns:
            print("A coluna 'Severity' não foi encontrada.")
            return

        # Usa .value_counts() para contar os valores únicos na coluna 'Severity'
        severity_counts = df['Severity'].value_counts()
        
        print(f"\nTotal de problemas encontrados: {len(df)}")
        print("\n--- Contagem por Nível de Severidade ---")
        print(severity_counts)

    except FileNotFoundError:
        print(f"Erro: O arquivo '{filename}' não foi encontrado.")
    except json.JSONDecodeError:
        print(f"Erro: O arquivo '{filename}' não é um JSON válido.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

# Executa a função
if __name__ == "__main__":
    analyze_trivy_json_report()
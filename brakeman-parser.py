import pandas as pd
import json

def analyze(filename="raw-data/baseline/brakeman-reports/brakeman-report.json"):
    """
    Analisa um relatório JSON do Brakeman e conta
    as vulnerabilidades por nível.
    """
    try:
        # Abre e carrega o arquivo JSON
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extrai a lista de 'warnings'
        warnings_list = data.get("warnings")

        if not warnings_list:
            print("Nenhuma vulnerabilidade (warnings) encontrada no relatório.")
            return

        # Carrega a lista de warnings diretamente em um DataFrame
        df = pd.DataFrame(warnings_list)

        # Verifica se a coluna 'confidence' existe
        if "confidence" not in df.columns:
            print("A coluna 'confidence' não foi encontrada nos warnings.")
            return
            
        # Pega o total de 'scan_info' para verificação
        total_warnings = data.get("scan_info", {}).get("security_warnings", 0)
        print(f"Total de vulnerabilidades encontradas: {total_warnings}\n")

        # Usa .value_counts() para contar os valores únicos na coluna 'confidence'
        confidence_counts = df['confidence'].value_counts()

        print("--- Contagem por Nível ---")
        print(confidence_counts)

        # Verificação opcional
        if confidence_counts.sum() != total_warnings:
            print(f"\nAviso: A soma das contagens ({confidence_counts.sum()}) não bate com o total ({total_warnings}).")

    except FileNotFoundError:
        print(f"Erro: O arquivo '{filename}' não foi encontrado.")
    except json.JSONDecodeError:
        print(f"Erro: O arquivo '{filename}' não é um JSON válido.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

# Executa a função
if __name__ == "__main__":
    analyze()
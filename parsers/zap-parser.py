import pandas as pd
import json

def analyze_zap_json_report(filename="../raw-data/baseline/zap-reports/baseline-report.json"):
    """
    Analisa um relatório JSON do OWASP ZAP, agrupa pelo 'riskcode'
    (o nível de risco principal) e soma o número de instâncias.
    """
    print(f"--- Analisando o relatório '{filename}' ---")
    
    try:
        # Abre e carrega o arquivo JSON
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Acessa a lista de alertas
        alerts_list = data.get("site", [{}])[0].get("alerts", [])

        if not alerts_list:
            print("Nenhuma lista de 'alerts' encontrada no relatório.")
            return

        # Carrega a lista de alertas (agrupados) em um DataFrame
        df = pd.DataFrame(alerts_list)

        # Mapeia os 'riskcode' (que são strings) para os nomes de Risco
        risk_map = {
            "3": "High",
            "2": "Medium",
            "1": "Low",
            "0": "Informational"
        }
        
        # Cria a nova coluna 'Risk Level' baseada no mapeamento
        # .get() previne erros se um 'riskcode' inesperado aparecer
        df['Risk Level'] = df['riskcode'].apply(lambda x: risk_map.get(x, f"Unknown ({x})"))

        # Converte a coluna 'count' (que é uma string) para número
        df['count'] = pd.to_numeric(df['count'])

        # Agrupa pelo novo 'Risk Level' e SOMA as 'count' (instâncias)
        severity_counts = df.groupby('Risk Level')['count'].sum()

        # Reordena o índice para seguir a ordem de severidade
        ordered_levels = ["High", "Medium", "Low", "Informational"]
        # .reindex() garante que todos os níveis apareçam, mesmo que tenham 0 alertas
        final_counts = severity_counts.reindex(ordered_levels, fill_value=0)

        print(f"\nTotal de instâncias de alertas encontradas: {df['count'].sum()}")
        print("\n--- Contagem de INSTÂNCIAS por Nível de Risco ---")
        print(final_counts)
        

    except FileNotFoundError:
        print(f"Erro: O arquivo '{filename}' não foi encontrado.")
    except json.JSONDecodeError:
        print(f"Erro: O arquivo '{filename}' não é um JSON válido.")
    except IndexError:
        print("Erro: A estrutura do JSON 'site' não era a esperada (pode estar vazia).")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

# Executa a função
if __name__ == "__main__":
    analyze_zap_json_report()
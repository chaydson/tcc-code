import pandas as pd
import os
import importlib.util
import sys

def load_module_from_path(module_name, file_path):
    """
    Função utilitária para importar arquivos Python que têm hífens no nome
    ou estão em caminhos específicos.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def orchestrate_integration():
    print("--- Iniciando Integração de Dados ---")

    timeline_file = "merge_timeline.csv"
    if not os.path.exists(timeline_file):
        print(f"ERRO: Arquivo '{timeline_file}' não encontrado. Rode o script de tempo primeiro.")
        return

    df_timeline = pd.read_csv(timeline_file)
    print(f"Timeline carregada: {len(df_timeline)} commits.")

    try:
        mod_brakeman = load_module_from_path("brakeman_parser", "brakeman-parser.py")
        mod_trivy = load_module_from_path("trivy_parser", "trivy-parser.py")
        mod_zap = load_module_from_path("zap_parser", "zap-parser.py")
        
        print("\nExecutando Parser do Brakeman...")
        df_brakeman = mod_brakeman.analyze_merges_brakeman()
        
        print("\nExecutando Parser do Trivy...")
        df_trivy = mod_trivy.analyze_merges_trivy()
        
        print("\nExecutando Parser do ZAP...")
        df_zap = mod_zap.analyze_merges_zap()
        
    except AttributeError:
        print("\nERRO: Certifique-se de que suas funções nos parsers estão retornando 'return df_final'.")
        return
    except FileNotFoundError as e:
        print(f"\nERRO: Arquivo de script não encontrado: {e}")
        return


    if df_brakeman is not None and not df_brakeman.empty:
        # Mantém commit_hash, prefixa o resto
        cols = [c for c in df_brakeman.columns if c != 'commit_hash']
        mapper = {c: f"brakeman_{c}" for c in cols}
        df_brakeman = df_brakeman.rename(columns=mapper)
    
    if df_trivy is not None and not df_trivy.empty:
        cols = [c for c in df_trivy.columns if c != 'commit_hash']
        mapper = {c: f"trivy_{c}" for c in cols}
        df_trivy = df_trivy.rename(columns=mapper)

    if df_zap is not None and not df_zap.empty:
        cols = [c for c in df_zap.columns if c != 'commit_hash']
        mapper = {c: f"zap_{c}" for c in cols}
        df_zap = df_zap.rename(columns=mapper)

    print("\nUnindo DataFrames...")
    
    df_final = df_timeline.merge(df_brakeman, on='commit_hash', how='left')
    df_final = df_final.merge(df_trivy, on='commit_hash', how='left')
    df_final = df_final.merge(df_zap, on='commit_hash', how='left')

    numeric_cols = df_final.select_dtypes(include=['number']).columns

    df_final[numeric_cols] = df_final[numeric_cols].fillna(0)

    output_filename = "dataset_final_consolidado.csv"
    df_final.to_csv(output_filename, index=False)
    
    print("\n" + "="*40)
    print(f"INTEGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"Arquivo salvo: {output_filename}")
    print(f"Dimensões: {df_final.shape[0]} linhas x {df_final.shape[1]} colunas")
    print("="*40)
    
    print(df_final.head())

if __name__ == "__main__":
    orchestrate_integration()
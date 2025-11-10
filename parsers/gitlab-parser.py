import json
import requests
import sys
import os
from datetime import datetime, timedelta, timezone
import time
from dotenv import load_dotenv 

load_dotenv()

TODAY = datetime.now()

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN") 
PROJECT_ID = os.getenv("PROJECT_ID")      
BASE_URL_GITLAB = os.getenv("BASE_URL_GITLAB")  

def check_env_vars():
    """Verifica se as variáveis de ambiente necessárias estão configuradas."""
    if not GITLAB_TOKEN:
        print("Erro: Variável 'GITLAB_TOKEN' não definida.")
        print("Por favor, configure o arquivo .env com seu token.")
        sys.exit(1)
    if not PROJECT_ID:
        print("Erro: Variável 'PROJECT_ID' não definida.")
        print("Adicione o ID do seu projeto no arquivo .env.")
        sys.exit(1)
    print("Variáveis GITLAB_TOKEN e PROJECT_ID carregadas.")


def fetch_jobs_for_pipeline(headers, pipeline_id):
    """Busca e retorna uma lista de todos os jobs para um único pipeline_id."""
    
    all_jobs = []
    page = 1
    
    api_url = f"{BASE_URL_GITLAB}/projects/{PROJECT_ID}/pipelines/{pipeline_id}/jobs"
    
    while True:
        params = {
            'per_page': 100,
            'page': page
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            if response.status_code == 404:
                print(f" (Aviso: Jobs não encontrados ou inacessíveis, status 404)")
                return [] 
                
            response.raise_for_status() 
            
            page_jobs = response.json()
            
            if not page_jobs:
                break 

            all_jobs.extend(page_jobs)
            page += 1
            
        except requests.exceptions.HTTPError as http_err:
            print(f" (Erro HTTP ao buscar jobs: {http_err})")
            return [] 
        except requests.exceptions.RequestException as err:
            print(f" (Erro de requisição ao buscar jobs: {err})")
            return [] 

    return all_jobs

def save_pipelines_and_nested_jobs():
    """Busca pipelines do branch 'main' dos últimos 14 dias e aninha seus jobs."""
    
    print(f"Iniciando coleta de pipelines (últimos 14 dias, branch 'main') do projeto: {PROJECT_ID}...")
    
    headers = {
        'PRIVATE-TOKEN': GITLAB_TOKEN
    }
    
    fourteen_days_ago_utc = datetime.now(timezone.utc) - timedelta(days=14)
    timestamp_filter = fourteen_days_ago_utc.isoformat()
    
    print(f"Filtrando pipelines criados após (created_after): {timestamp_filter}")
    
    all_pipelines = []
    page = 1
    
    api_url_pipelines = f"{BASE_URL_GITLAB}/projects/{PROJECT_ID}/pipelines"

    while True:
        params = {
            'per_page': 100,
            'page': page,
            'order_by': 'id',
            'sort': 'desc',
            'ref': 'main',
            'created_after': timestamp_filter 
        }
        
        try:
            response = requests.get(api_url_pipelines, headers=headers, params=params, timeout=10)
            response.raise_for_status() 

            page_pipelines = response.json()
            
            if not page_pipelines:
                print(f"Página {page} vazia. Coleta de pipelines concluída.")
                break

            all_pipelines.extend(page_pipelines)
            print(f"Página {page}: {len(page_pipelines)} pipelines carregados. Total: {len(all_pipelines)}")
            
            page += 1

        except requests.exceptions.HTTPError as http_err:
            print(f"Erro HTTP Fatal ao buscar pipelines: {http_err} - {response.text}")
            return 
        except requests.exceptions.RequestException as err:
            print(f"Erro de requisição Fatal ao buscar pipelines: {err}")
            return

    print(f"\nQuantidade total de pipelines (últimos 14 dias, 'main') coletados: {len(all_pipelines)}")

    if not all_pipelines:
        print("Nenhum pipeline foi encontrado.")
        return

    print("\nIniciando coleta de jobs para cada pipeline (isso pode demorar)...")
    
    total_pipelines = len(all_pipelines)
    for i, pipeline in enumerate(all_pipelines):
        pipeline_id = pipeline['id']
        
        print(f"Buscando jobs... [Pipeline {i+1}/{total_pipelines}, ID: {pipeline_id}]", end="", flush=True)
        
        jobs_list = fetch_jobs_for_pipeline(headers, pipeline_id)
        
        pipeline['jobs'] = jobs_list
        
        print(f" -> {len(jobs_list)} jobs encontrados.")
        
        time.sleep(0.1) 

    print("\nColeta de jobs finalizada.")

    print("Salvando arquivo JSON unificado...")
    
    output_dir = './analytics-raw-data'
    os.makedirs(output_dir, exist_ok=True)
    
    safe_project_name = PROJECT_ID.replace('%2F', '-')
    
    file_path = f'{output_dir}/GitLab_API-Pipelines-With-Jobs-MAIN-14Days-{safe_project_name}-{TODAY.strftime("%Y-%m-%d-%H%M%S")}.json'

    try:
        with open(file_path, 'w', encoding='utf-8') as fp:
            json.dump(all_pipelines, fp, indent=4, ensure_ascii=False)
        
        print(f"Arquivo salvo com sucesso em: {file_path}")
    
    except IOError as e:
        print(f"Erro ao salvar o arquivo: {e}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu ao salvar o arquivo: {e}")

if __name__ == "__main__":
    print("Iniciando script de coleta (Pipelines + Jobs)...")
    check_env_vars()
    save_pipelines_and_nested_jobs()
    print("Script finalizado.")
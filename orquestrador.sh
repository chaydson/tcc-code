#!/bin/bash

# O caminho para o repositório do BP
REPO_DIR="/home/chaydson/Workspace/UnB/TCC/decidim-govbr-lappis"

# O caminho ABSOLUTO para o seu script 'run_local_ci'
RUNNER_SCRIPT_PATH="/home/chaydson/Workspace/UnB/TCC/tcc-code/run_local_ci.sh"

# O caminho para o .gitlab-ci.yml 
CI_FILE_PATH="/home/chaydson/Workspace/UnB/TCC/tcc-code/.gitlab-ci.yml"

# Onde salvar os relatórios históricos
MASTER_REPORTS_DIR="/home/chaydson/Workspace/UnB/TCC/tcc-code/raw-data/merges"

# Nome da branch principal
BRANCH_NAME="main"

# Garante que o script de execução tenha permissão
chmod +x "$RUNNER_SCRIPT_PATH"
mkdir -p "$MASTER_REPORTS_DIR"

echo "Iniciando coleta de dados históricos..."
echo "Repositório: $REPO_DIR"
echo "Relatórios mestres serão salvos em: $MASTER_REPORTS_DIR"

# Obter Lista de Commits
echo "Buscando commits de merge dos últimos 86 dias em '$BRANCH_NAME'..."

# Entra no diretório do repo para rodar comandos git
cd "$REPO_DIR"
if [ $? -ne 0 ]; then
  echo "❌ ERRO: Não foi possível acessar o diretório do repositório: $REPO_DIR"
  exit 1
fi

COMMITS=$(git log "$BRANCH_NAME" --merges --since="86 days ago" --pretty=format:"%H")

if [ -z "$COMMITS" ]; then
  echo "Nenhum commit de merge encontrado nos últimos 14 dias."
  exit 0
fi

echo "Commits encontrados:"
echo "$COMMITS"
echo ""

for COMMIT_HASH in $COMMITS; do
  echo ""
  echo "======================================================================="
  echo "🚀 Processando Commit: $COMMIT_HASH"
  echo "======================================================================="

  # Define o caminho de destino
  COMMIT_REPORT_DIR="$MASTER_REPORTS_DIR/$COMMIT_HASH"
  
  # Verifica se o diretório de relatório já existe
  if [ -d "$COMMIT_REPORT_DIR" ]; then
    echo "↪️  AVISO: Relatórios já encontrados em $COMMIT_REPORT_DIR."
    echo "Pulando a re-execução para este commit."
    continue # Pula para o próximo commit no loop
  fi

  # Garante que estamos no diretório certo e limpa o estado
  cd "$REPO_DIR"
  git reset --hard HEAD
  git checkout "$BRANCH_NAME" --force > /dev/null 2>&1
  git pull > /dev/null 2>&1
  
  # Checkout do commit antigo
  echo "Fazendo checkout do commit $COMMIT_HASH..."
  git checkout "$COMMIT_HASH" --force
  if [ $? -ne 0 ]; then
      echo "⚠️ ERRO: Falha ao fazer checkout do commit $COMMIT_HASH. Pulando."
      continue
  fi

  # Injeta os arquivos necessários (script e CI)
  echo "Injetando arquivos de CI (.gitlab-ci.yml e run_local_ci.sh)..."
  cp "$CI_FILE_PATH" "$REPO_DIR/.gitlab-ci.yml"
  cp "$RUNNER_SCRIPT_PATH" "$REPO_DIR/run_local_ci.sh"
  chmod +x "$REPO_DIR/run_local_ci.sh"
  
  if [ $? -ne 0 ]; then
      echo "⚠️ ERRO: Falha ao copiar arquivos de CI. Pulando."
      continue
  fi

  # Roda o run_local_ci.sh
  echo "Executando 'run_local_ci.sh' para $COMMIT_HASH..."
  (cd "$REPO_DIR" && ./run_local_ci.sh)
  RUN_STATUS=$?
  echo "Execução concluída para $COMMIT_HASH com status: $RUN_STATUS"

  mkdir -p "$COMMIT_REPORT_DIR"
  
  # Move os logs da pipeline
  if [ -d "$REPO_DIR/report-pipeline-local" ]; then
    echo "Arquivando logs de 'report-pipeline-local'..."
    mv "$REPO_DIR/report-pipeline-local" "$COMMIT_REPORT_DIR/logs_pipeline"
  else
    echo "Aviso: Diretório 'report-pipeline-local' não encontrado."
  fi
  
  # Move os artefatos
  if [ -d "$REPO_DIR/reports" ]; then
    echo "Arquivando artefatos de 'reports'..."
    mv "$REPO_DIR/reports" "$COMMIT_REPORT_DIR/artifacts"
  else
    echo "Aviso: Diretório 'reports' não encontrado."
  fi

  echo "Relatórios para $COMMIT_HASH salvos em: $COMMIT_REPORT_DIR"

done

# Limpeza Final 
echo "======================================================================="
echo "✅ Processo concluído."
echo "Retornando para a branch $BRANCH_NAME..."
cd "$REPO_DIR"
git checkout "$BRANCH_NAME" --force
git reset --hard "origin/$BRANCH_NAME"

echo "Todos os relatórios estão em: $MASTER_REPORTS_DIR"
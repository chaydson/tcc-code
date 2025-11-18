#!/bin/bash

REPORTS_DIR="report-pipeline-local"
REPORTS_TOOLS_DIR="reports"
SUMMARY_FILE="$REPORTS_DIR/pipeline_summary.txt"

fix_reports_permissions() {
  echo "-----------------------------------------------------------------------"
  echo "FIX: Restaurando posse e permissões de '$REPORTS_TOOLS_DIR/'..."
  
  sudo chown -R $USER:$USER "$REPORTS_TOOLS_DIR"
  sudo chmod -R 777 "$REPORTS_TOOLS_DIR"
  
  echo "FIX: Permissões de '$REPORTS_TOOLS_DIR/' restauradas."
}

mkdir -p "$REPORTS_DIR"

echo "Garantindo permissões em $REPORTS_DIR"
fix_reports_permissions

rm -f "$REPORTS_DIR"/*_full_output.txt
> "$SUMMARY_FILE" 

echo "Salvando relatórios em: $REPORTS_DIR/"
echo "Resumo centralizado em: $SUMMARY_FILE"

OVERALL_STATUS=0
trap cleanup EXIT

header() {
  echo ""
  echo "======================================================================="
  echo "🚀 EXECUTANDO JOB: $1"
  echo "======================================================================="
  echo ""
}

run_and_capture() {
  local job_name="$1"
  shift 1 
  local command_to_run=("$@") 
  local safe_name=$(echo "$job_name" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_')
  local output_filepath="$REPORTS_DIR/${safe_name}_full_output.txt"

  header "$job_name"
  echo "Comando: ${command_to_run[*]}"
  echo "Log completo: $output_filepath"
  echo "Resumo será salvo em: $SUMMARY_FILE"
  echo "-----------------------------------------------------------------------"

  "${command_to_run[@]}" 2>&1 | tee "$output_filepath"
  local job_status=${PIPESTATUS[0]}

  echo "--- Job: $job_name ---" >> "$SUMMARY_FILE"
  grep -E "^ *(PASS|FAIL|WARN)" "$output_filepath" >> "$SUMMARY_FILE"

  local grep_status=$?
  
  if [ $grep_status -ne 0 ]; then
    if [ $job_status -eq 0 ]; then
      echo "JOB_SUCCESS (Nenhuma linha PASS/FAIL/WARN encontrada)" >> "$SUMMARY_FILE"
    else
      echo "JOB_FAILED (Exit code: $job_status. Nenhuma linha PASS/FAIL/WARN encontrada)" >> "$SUMMARY_FILE"
    fi
  fi

  echo "" >> "$SUMMARY_FILE"

  echo "Job '$job_name' concluído com código de saída: $job_status"
  
  return $job_status
}

cleanup() {
  echo ""
  echo "======================================================================="
  echo "🧹 EXECUTANDO LIMPEZA DE AMBIENTE..."
  echo "======================================================================="
  
  echo "Parando containers Docker e removendo volumes..."
  docker compose down -v --remove-orphans
  docker container prune -f
  docker volume prune -f
  docker image prune -a -f
  docker builder prune -f
  echo ""
  echo "Limpeza de Docker concluída."
}

# --- SAST ---
run_and_capture "SAST" \
  gitlab-ci-local --volume "/var/run/docker.sock:/var/run/docker.sock" --variable "DOCKER_HOST=unix:///var/run/docker.sock" SAST
if [ $? -ne 0 ]; then
  echo "⚠️ Job 'SAST' falhou, mas continuando..."
  OVERALL_STATUS=1
fi
fix_reports_permissions

# --- SCA ---
run_and_capture "SCA" \
  gitlab-ci-local SCA
if [ $? -ne 0 ]; then
  echo "⚠️ Job 'SCA' falhou, mas continuando..."
  OVERALL_STATUS=1
fi
fix_reports_permissions

# --- DAST ---
header "SETUP DAST: Limpando ambiente Docker (para evitar cache corrompido)"
echo "Parando containers e limpando volumes (-v)..."
docker compose down -v
if [ $? -ne 0 ]; then
    echo "⚠️ Aviso: Falha ao executar 'docker compose down -v'. Continuando mesmo assim..."
fi

echo "Reconstruindo a imagem de serviço sem cache (--no-cache)..."
docker compose build --no-cache decidim-service
BUILD_STATUS=$?

if [ $BUILD_STATUS -ne 0 ]; then
  echo "❌ Falha crítica ao reconstruir a imagem 'decidim-service' com 'build --no-cache'."
  echo "Impossível continuar com o DAST. Verifique os logs de build."
  APP_RUN_STATUS=1
else
  APP_RUN_STATUS=0
fi

header "SETUP DAST: Subindo aplicação via Docker Compose"

if [ $APP_RUN_STATUS -eq 0 ]; then
  echo "Subindo aplicação com 'docker compose up -d'..."
  docker compose up -d
  APP_RUN_STATUS=$?
else
  echo "Pulando 'docker compose up' devido à falha no 'build'."
fi

if [ $APP_RUN_STATUS -ne 0 ]; then
  echo "❌ Falha ao iniciar a aplicação com 'docker compose up' (ou falha no build anterior). Abortando DAST."
  docker compose logs decidim-service
  OVERALL_STATUS=1
else
  echo "Aplicação iniciada. Aguardando até o servidor subir..."
  
  ATTEMPTS=0
  MAX_ATTEMPTS=100
  APP_IS_READY_FOR_DAST=false
  RESTART_ATTEMPTS=0
  MAX_RESTARTS=2

  while [ $ATTEMPTS -le $MAX_ATTEMPTS ]; do
    
    # Tenta o curl
    if curl -f -s -o /dev/null http://localhost:3000; then
      echo "✅ Aplicação pronta em http://localhost:3000."
      APP_IS_READY_FOR_DAST=true
      break # Sucesso, sai do loop
    fi

    # Verifica o status do container 'decidim-service'
    CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' decidim-service 2>/dev/null || echo "not_found")
    
    if [ "$CONTAINER_STATUS" = "exited" ]; then
      echo "⚠️ AVISO: O container 'decidim-service' parou (Status: $CONTAINER_STATUS) na tentativa $ATTEMPTS."
      echo "Mostrando logs da falha:"
      docker compose logs decidim-service
      
      RESTART_ATTEMPTS=$((RESTART_ATTEMPTS + 1))
      
      if [ $RESTART_ATTEMPTS -gt $MAX_RESTARTS ]; then
         echo "❌ ERRO CRÍTICO: O container parou e o limite de restarts ($MAX_RESTARTS) foi atingido."
         OVERALL_STATUS=1
         break
      fi

      echo "🔄 Tentando reiniciar a aplicação (Restart $RESTART_ATTEMPTS/$MAX_RESTARTS)..."
      
      # Derruba o ambiente
      echo "Executando 'docker compose down'..."
      docker compose down
      
      # Tenta subir novamente
      echo "Executando 'docker compose up -d'..."
      docker compose up -d
      RESTART_STATUS=$?
      
      if [ $RESTART_STATUS -ne 0 ]; then
          echo "❌ Falha crítica ao tentar reiniciar com 'docker compose up -d' após o crash."
          OVERALL_STATUS=1
          break
      fi
      
      echo "Reinício concluído. Aguardando estabilização antes da próxima checagem..."
      sleep 10
    
    fi

    ATTEMPTS=$((ATTEMPTS + 1))
    
    # Checagem de timeout
    if [ $ATTEMPTS -gt $MAX_ATTEMPTS ]; then
      echo "❌ Timeout: Aplicação não respondeu em http://localhost:3000 após 90 segundos."
      docker compose logs
      OVERALL_STATUS=1
      break
    fi

    echo "Aguardando... (tentativa $ATTEMPTS/$MAX_ATTEMPTS) (Status do container: $CONTAINER_STATUS)"
    sleep 5
  done

  if [ "$APP_IS_READY_FOR_DAST" = true ]; then
    echo "Iniciando DAST."
    run_and_capture "DAST (ZAP Baseline)" \
      sudo docker run --network="host" --rm \
      -v $(pwd):/zap/wrk/:rw -t \
      ghcr.io/zaproxy/zaproxy:stable \
      zap-baseline.py \
        -t http://localhost:3000/ \
        -r "$REPORTS_TOOLS_DIR/zap-report.html" \
        -J "$REPORTS_TOOLS_DIR/zap-report.json" \
        -l WARN

    ZAP_STATUS=$?    
    echo "Job 'DAST (ZAP Baseline)' (Código de Saída: $ZAP_STATUS)"
  else
    echo "Pulando DAST devido a falha no container ou timeout."
  fi

fi
fix_reports_permissions

echo ""
echo "======================================================================="
echo "Resumo da Pipeline (de $SUMMARY_FILE):"
echo "======================================================================="
cat "$SUMMARY_FILE"
echo "======================================================================="

if [ $OVERALL_STATUS -eq 0 ]; then
  echo "✅ Pipeline local concluída com SUCESSO!"
else
  echo "❌ Pipeline local concluída com FALHAS."
  echo "Verifique o log completo em '$REPORTS_DIR/' para detalhes."
fi
echo "======================================================================="

exit $OVERALL_STATUS
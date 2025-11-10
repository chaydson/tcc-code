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
if [ $? -ne 0 ]; then
  echo "❌ Falha ao obter permissões de sudo para $REPORTS_DIR. Abortando."
  exit 1
fi

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
  echo "🧹 EXECUTANDO LIMPEZA DE IMAGENS DOCKER..."
  echo "======================================================================="
  echo "Removendo todas as imagens Docker não utilizadas (prune)..."
  docker image prune -a -f
  
  echo ""
  echo "Limpeza de Docker concluída."
  
  fix_reports_permissions
}


run_and_capture "Lint" \
  gitlab-ci-local Lint
if [ $? -ne 0 ]; then
  echo "❌ Job 'Lint' FALHOU. Abortando pipeline."
  OVERALL_STATUS=1
  exit 1 
fi
fix_reports_permissions


run_and_capture "SAST" \
  gitlab-ci-local --volume "/var/run/docker.sock:/var/run/docker.sock" --variable "DOCKER_HOST=unix:///var/run/docker.sock" SAST
if [ $? -ne 0 ]; then
  echo "⚠️ Job 'SAST' falhou, mas continuando..."
  OVERALL_STATUS=1
fi
fix_reports_permissions


run_and_capture "SCA" \
  gitlab-ci-local SCA
if [ $? -ne 0 ]; then
  echo "⚠️ Job 'SCA' falhou, mas continuando..."
  OVERALL_STATUS=1
fi
fix_reports_permissions


run_and_capture "Build" \
  gitlab-ci-local --force-shell-executor Build
if [ $? -ne 0 ]; then
  echo "❌ Job 'Build' FALHOU. Abortando pipeline."
  OVERALL_STATUS=1
  exit 1
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

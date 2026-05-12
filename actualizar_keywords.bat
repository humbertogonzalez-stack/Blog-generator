@echo off
REM ============================================================
REM actualizar_keywords.bat — Clivi SEO Motor
REM Corre cada domingo noche automaticamente
REM
REM Programar en Task Scheduler:
REM  - Programa: actualizar_keywords.bat
REM  - Frecuencia: semanal, domingos 11pm
REM ============================================================

echo.
echo ============================================================
echo  CLIVI SEO MOTOR — Actualizacion semanal de keywords
echo  %date% %time%
echo ============================================================
echo.

REM Carpeta del proyecto
cd /d "C:\Users\lap\Downloads\CLIVI\Organico\Semana_3_29_al_5_de_mayo\Generador"

REM Activar Anaconda base
call conda activate base

REM Paso 1: Actualizar scores con GSC + Trends
echo [1/2] Actualizando scores con GSC y Google Trends...
python gsc_connector.py
echo.

REM Paso 2: Subir keywords al KV de Cloudflare
echo [2/2] Subiendo keywords al KV de Cloudflare...
pnpm wrangler kv key put --namespace-id 2e6cee17ffad4d03b3aed30cf8fda716 "pending-keywords" --path trends_batch.json --remote
echo.

echo ============================================================
echo  Listo. El cron del lunes generara los articulos.
echo ============================================================
echo.

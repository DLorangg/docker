import os
from pathlib import Path
import subprocess
import requests
import json
from supabase import create_client, Client

# ----------------------------------------------------
# -- FASE 1: DATOS DE PRUEBA (HARDCODED) --
# ----------------------------------------------------

VIDEO_URL = os.environ.get("VIDEO_URL") 
JOB_ID = os.environ.get("JOB_ID")

# Pega aquÃ­ el array de clips que obtuviste de n8n en la fase anterior
CLIPS_JSON_STRING = os.environ.get("CLIPS_JSON_STRING")

SUPABASE_URL = "https://krlzqmfmqwwrzghgiepq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtybHpxbWZtcXd3cnpnaGdpZXBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM1MzY0NywiZXhwIjoyMDcxOTI5NjQ3fQ.NfH0F3zEF9TfGT77LaBBjMUlZQuVdSlEcc7f38LL4VE"

# ----------------------------------------------------
# -- FASE 2: LÃ“GICA DEL SCRIPT --
# ----------------------------------------------------

def upload_clip_manually(supabase_url, supabase_key, bucket, dest_path, file_path):
    url = f"{supabase_url}/storage/v1/object/{bucket}/{dest_path}"
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "video/mp4",
        "x-upsert": "true"
    }

    with open(file_path, 'rb') as f:
        data = f.read()
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status() # Esto lanzarÃ¡ un error si la subida falla

def main():
    # --- InicializaciÃ³n ---
    print("Inicializando cliente de Supabase...")
   
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) 

    workspace = Path(f"/workspace/{JOB_ID}")
    workspace.mkdir(parents=True, exist_ok=True)
    original_video_path = workspace / "original.mp4"
    normalized_video_path = workspace / "normalized.mp4"

    clips_to_process = json.loads(CLIPS_JSON_STRING)
    
    # --- Descargar Video Original ---
    print(f"Descargando video original desde {VIDEO_URL}...")
    r = requests.get(VIDEO_URL, stream=True)
    r.raise_for_status()
    with open(original_video_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Video original descargado.")

    # --- Paso de NormalizaciÃ³n del Video ---
    print("\n--- NORMALIZANDO EL VIDEO ORIGINAL ---")
    try:
        normalize_cmd = (
            f"ffmpeg -y -i {original_video_path} "
            f"-fflags +genpts -r 30 -c:v libx264 -pix_fmt yuv420p -c:a aac "
            f"{normalized_video_path}"
        )
        subprocess.run(normalize_cmd, shell=True, check=True, capture_output=True, text=True)
        print("Video normalizado con Ã©xito.")
    except subprocess.CalledProcessError as e:
        print(f"âŒ Error al normalizar el video: {e.stderr}")
        return

    # --- Bucle para Cortar y Subir Clips ---
    print("\n--- INICIANDO PROCESO DE RECORTE ---")
    output_bucket = "generated-clips"

    for i, clip_data in enumerate(clips_to_process):
        start_time = clip_data["start"]
        end_time = clip_data["end"]
        clip_filename = f"clip_{i+1}.mp4"
        output_path = workspace / clip_filename
        duration = end_time - start_time

        print(f"\n[Clip {i+1}/{len(clips_to_process)}] Creando '{clip_filename}' (Inicio: {start_time}s, DuraciÃ³n: {duration}s)")
        
        ffmpeg_cmd = (
            f"ffmpeg -y -ss {start_time} "
            f"-i {normalized_video_path} "
            f"-t {duration} "
            f"-c:v libx264 -c:a aac "
            f"{output_path}"
        )
        
        try:
            subprocess.run(ffmpeg_cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"'{clip_filename}' creado con Ã©xito.")

            # --- NUEVO MÃ‰TODO DE SUBIDA MANUAL ---
            upload_path = f"{JOB_ID}/{clip_filename}"
            print(f"Subiendo a Supabase en '{upload_path}'...")
            upload_clip_manually(SUPABASE_URL, SUPABASE_KEY, output_bucket, upload_path, output_path)
            print("Subida completada.")

        except subprocess.CalledProcessError as e:
            print(f"âŒ Error al procesar el clip {i+1}: {e.stderr}")
            continue
        except Exception as e:
            print(f"âŒ Un error inesperado ocurriÃ³ con el clip {i+1}: {str(e)}")
            continue

    print("\n--- PROCESO DE RECORTE FINALIZADO ---")

if __name__ == "__main__":
    main()
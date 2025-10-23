#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
from pathlib import Path
import requests
from supabase import create_client, Client

# -------------------------
# LOAD ENVIRONMENT VARIABLES
# -------------------------
class Args:
    video_url = os.environ.get("VIDEO_URL")
    whisper_model = os.environ.get("WHISPER_MODEL", "small") # "small" es un valor por defecto
    language = os.environ.get("LANGUAGE", "es")
    out_prefix = os.environ.get("OUT_PREFIX")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    job_id = os.environ.get("JOB_ID")

args = Args()

# Chequeo simple para asegurarse que las variables requeridas existen
if not all([args.video_url, args.out_prefix, args.supabase_url, args.supabase_key, args.job_id]):
    print("âŒ Error: Faltan una o mÃ¡s variables de entorno requeridas.")
    sys.exit(1) # Termina el script si falta algo esencial

# -------------------------
# INICIALIZAR CLIENTE DE SUPABASE
# -------------------------
print("Inicializando cliente de Supabase...")
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
print("Cliente de Supabase inicializado.")

workspace = Path("/workspace")
out_path = workspace / args.out_prefix
out_path.mkdir(parents=True, exist_ok=True)

video_file = out_path / "video.mp4"
audio_file = out_path / "audio.wav"

# -------------------------
# DESCARGAR VIDEO
# -------------------------
print(f"Descargando video desde {args.video_url}...")
r = requests.get(args.video_url, stream=True)
r.raise_for_status()
with open(video_file, "wb") as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)
print("Video descargado!")

# -------------------------
# EXTRAER AUDIO
# -------------------------
print("Extrayendo audio con ffmpeg...")
subprocess.run(f"ffmpeg -y -i {video_file} -ar 16000 -ac 1 {audio_file}", shell=True, check=True)
print("Audio extraÃ­do!")

# -------------------------
# EJECUTAR WHISPER
# -------------------------
print("Ejecutando Whisper...")
whisper_cmd = (
    f"whisper {audio_file} "
    f"--model {args.whisper_model} "
    f"--language {args.language} "
    f"--output_dir {out_path} "
    f"--output_format all"
)
subprocess.run(whisper_cmd, shell=True, check=True)
print("Whisper finalizado!")

# -------------------------
# SUBIR OUTPUTS A SUPABASE
# -------------------------
print("Subiendo archivos generados a Supabase Storage...")

def upload_to_supabase(local_path: Path, bucket: str, dest_path: str):
    with open(local_path, "rb") as f:
        supabase.storage.from_(bucket).upload(dest_path, f, {"upsert": "true"})
    public_url = supabase.storage.from_(bucket).get_public_url(dest_path)
    return public_url

bucket = "transcripts"

files = {
    "srt": out_path / "audio.srt",
    "txt": out_path / "audio.txt",
    "vtt": out_path / "audio.vtt",
    "json": out_path / "audio.json",
    "audio": audio_file
}

uploaded_outputs = {}

for name, path in files.items():
    if path.exists():
        dest = f"{args.out_prefix}/{path.name}"
        url = upload_to_supabase(path, bucket, dest)
        uploaded_outputs[name] = url
    else:
        print(f"âš ï¸ Archivo no encontrado: {path}")

# -------------------------
# ACTUALIZAR SUPABASE
# -------------------------
print("Actualizando registro en Supabase...")

try:
    # Descarga de video, extracciÃ³n de audio, ejecuciÃ³n de Whisper...
    # Subida a Supabase Storage
    # ActualizaciÃ³n de status = "done"
    res = supabase.table("trans_jobs").update({
        "outputs": uploaded_outputs,
        "status": "transcribed",
        "error_msg": None  # Limpiamos cualquier error previo
    }).eq("id", args.job_id).execute()

    print("âœ… Supabase actualizado correctamente!")

except Exception as e:
    # Capturamos cualquier excepciÃ³n y la guardamos en Supabase
    supabase.table("trans_jobs").update({
        "status": "error",
        "error_msg": str(e)
    }).eq("id", args.job_id).execute()
    print("âŒ OcurriÃ³ un error:", e)
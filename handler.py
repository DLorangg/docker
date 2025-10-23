import runpod
import subprocess
import os
import json

# Este es el manejador que RunPod llamarÃ¡ automÃ¡ticamente
def handler(event):
    # 'event' es el objeto 'input' que enviamos desde n8n
    job_input = event['input']
    
    # Sacamos el nombre del script que queremos correr
    script_to_run = job_input.pop('script_to_run', None)

    # Convertimos el resto de los datos del 'input' en variables de entorno
    # para que nuestros scripts existentes puedan leerlas sin cambios.
    print("Estableciendo variables de entorno...")
    for key, value in job_input.items():
        # Asegurarnos de que todo sea un string para el entorno
        os.environ[key.upper()] = str(value)
        
    print(f"Variable SCRIPT_TO_RUN recibida: {script_to_run}")

    # Decidir quÃ© script ejecutar
    if script_to_run == 'transcribe':
        print("Iniciando 'process_job.py'...")
        result = subprocess.run(["python3", "process_job.py"], capture_output=True, text=True)
    elif script_to_run == 'clip':
        print("Iniciando 'process_clips.py'...")
        result = subprocess.run(["python3", "process_clips.py"], capture_output=True, text=True)
    else:
        print("Error: script_to_run no es vÃ¡lido o no se especificÃ³.")
        return {"error": f"script_to_run '{script_to_run}' no es vÃ¡lido."}

    # Imprimir la salida de los scripts para depuraciÃ³n
    print("Salida del script:")
    print(result.stdout)
    if result.stderr:
        print("Errores del script:")
        print(result.stderr)

    return {"status": "completed", "output": result.stdout, "errors": result.stderr}

# Esto inicia el servidor de RunPod y le dice que use nuestra funciÃ³n 'handler'
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
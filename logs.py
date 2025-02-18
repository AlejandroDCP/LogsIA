import requests
import json
import time
import boto3
#cliente s3 y bedrock
s3_client = boto3.client("s3")

bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

#Config URL LOKI y s3 
LOKI_URL = "http://172.19.2.12:3100/loki/api/v1/query_range"
S3_BUCKET = "cadu-mylogs"  
S3_FOLDER = "loki_logs"

#registro de los ultimos 10 min y filtrar por el tag de error
# start_time = int(time.time() - 600) * 1_000_000_000 
params = {
    "query": '{host="Corp_Cancun-1"}|~ "level=\\\"error\\\""',
    "limit": 10 
    # "start": start_time
}

response = requests.get(LOKI_URL, params=params)
logs = response.json()

# Extraer solo los mensajes de error
log_messages = [
    entry[1] for stream in logs.get("data", {}).get("result", [])
    for entry in stream.get("values", [])
]
# Convertir logs a JSON para almacenar en S3
log_data = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
    "logs": log_messages
}
log_json = json.dumps(log_data, indent=4)

#temp 

log_filename = f"./tmp/loki_errors_{int(time.time())}.json"
with open(log_filename, "w") as file:
    file.write(log_json)

# Subir a S3

s3_key = f"{S3_FOLDER}/loki_logs/{int(time.time())}.json"
s3_client.upload_file(log_filename, S3_BUCKET, s3_key)

# print(f"Logs guardados en S3: s3://{S3_BUCKET}/{s3_key}")
print("log extraido")

### interpretr log de loki con modelos de Bedrock 

# # Listar los objetos en el folder de S3
response = s3_client.list_objects_v2(
    Bucket=S3_BUCKET,
    Prefix=S3_FOLDER
)

# Obtener el archivo más reciente
files = response.get('Contents', [])
if files:
    latest_file = max(files, key=lambda x: x['LastModified'])
    latest_file_key = latest_file['Key']
    print(f"Último archivo guardado: {latest_file_key}")
else:
    print("No se encontraron archivos en el bucket.")
# Descargar el archivo más reciente desde S3
response = s3_client.get_object(Bucket=S3_BUCKET, Key=latest_file_key)
log_data = response['Body'].read().decode('utf-8')

# Imprimir contenido 
print(log_data)



# Preparar el prompt para Bedrock 
prompt = f"Analiza estos logs evento por evento y dame posibles soluciones, solo respuestas en español:\n{log_data}"

# Enviar los logs a Bedrock para interpretación
response = bedrock_client.invoke_model(
    modelId='amazon.titan-text-premier-v1:0',  
    contentType='application/json',
    accept='application/json',
    body=json.dumps({
       "inputText": prompt
    }
    )
)

# Obtener y mostrar la respuesta de Bedrock
analys = response['body'].read().decode()
print("Análisis de Bedrock:", analys)

 
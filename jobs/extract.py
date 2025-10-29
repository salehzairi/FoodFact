import argparse, io, boto3
from airflow.hooks.base import BaseHook

# Petit CSV d’exemple qu’on va créer et envoyer vers MinIO
CSV_CONTENT = """id,name,qty
1, apple ,5
2,Banana, 0
3,Orange,3
4, pear,  2
"""

def main(date_str: str):
    # Récupération de la connexion MinIO à partir d’Airflow
    conn = BaseHook.get_connection("minio_default")
    endpoint = conn.extra_dejson.get("endpoint_url") or conn.extra_dejson.get("host")
    bucket = conn.extra_dejson.get("bucket", "data")

    # Création du client S3 (ici utilisé pour communiquer avec MinIO)
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=conn.login,
        aws_secret_access_key=conn.password,
        region_name=(conn.extra_dejson.get("region_name", "us-east-1").strip() if conn else "us-east-1"),
    )

    # Chemin (clé) où le CSV sera déposé dans le bucket
    key = f"landing/foodfacts/{date_str}/raw.csv"

    # Envoi du fichier vers MinIO (dans la zone landing)
    s3.upload_fileobj(io.BytesIO(CSV_CONTENT.encode("utf-8")), bucket, key)
    print(f"[extract] Fichier CSV envoyé

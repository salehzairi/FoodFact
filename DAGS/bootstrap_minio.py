# dags/bootstrap_minio.py
from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    dag_id="bootstrap_minio",
    description="Idempotent : s’assure que le bucket MinIO et les préfixes requis existent",
    start_date=datetime(2025, 1, 1),
    schedule_interval="@once",
    catchup=False,
    tags=["infra", "minio", "bootstrap"],
    default_args={"retries": 0},  # explicite : on échoue rapidement pour voir l’erreur réelle
) as dag:

    def ensure_bucket_and_prefixes():
        import os
        import json
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        try:
            from airflow.hooks.base import BaseHook
        except Exception:
            BaseHook = None

        # --------- 1) Charger la configuration (depuis la connexion Airflow si elle existe, sinon valeurs par défaut) ----------
        conn_id = "minio_default"
        cfg = {
            "endpoint": "http://minio:9000",
            "bucket": "data",
            "region": "us-east-1",
            "access_key": "minio",
            "secret_key": "minio123",
            "source": "defaults",
        }

        if BaseHook is not None:
            try:
                conn = BaseHook.get_connection(conn_id)
                extra = conn.extra_dejson or {}
                cfg.update({
                    "endpoint": extra.get("endpoint_url") or extra.get("host") or cfg["endpoint"],
                    "bucket":   extra.get("bucket", cfg["bucket"]),
                    "region":   extra.get("region_name", cfg["region"]),
                    "access_key": conn.login or cfg["access_key"],
                    "secret_key": conn.password or cfg["secret_key"],
                    "source": "airflow_connection",
                })
            except Exception as e:
                print(f"[bootstrap_minio] Connexion '{conn_id}' introuvable ou inutilisable, utilisation des valeurs par défaut. Err={e}")

        print("[bootstrap_minio] Configuration effective :", json.dumps({
            "endpoint": cfg["endpoint"],
            "bucket": cfg["bucket"],
            "region": cfg["region"],
            "source": cfg["source"],
        }))

        # IMPORTANT pour MinIO : utiliser le mode path-style + signature v4
        boto_cfg = Config(s3={"addressing_style": "path"}, signature_version="s3v4")

        s3 = boto3.client(
            "s3",
            endpoint_url=cfg["endpoint"],             # doit être http://minio:9000 dans le réseau Docker
            aws_access_key_id=cfg["access_key"],
            aws_secret_access_key=cfg["secret_key"],
            region_name=cfg["region"],
            config=boto_cfg,
        )

        # --------- 2) Vérifier ou créer le bucket (idempotent) ----------
        try:
            s3.head_bucket(Bucket=cfg["bucket"])
            print(f"[bootstrap_minio] Le bucket existe déjà : {cfg['bucket']}")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            print(f"[bootstrap_minio] head_bucket a échoué ({code}); tentative de création...")
            try:
                # Pour us-east-1, pas besoin de LocationConstraint
                s3.create_bucket(Bucket=cfg["bucket"])
                print(f"[bootstrap_minio] Bucket créé : {cfg['bucket']}")
            except ClientError as ce:
                code2 = ce.response.get("Error", {}).get("Code", "")
                if code2 in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    print(f"[bootstrap_minio] Bucket déjà présent ({code2}), on continue.")
                else:
                    raise

        # --------- 3) Créer les préfixes nécessaires ----------
        prefixes = [
            "landing/foodfacts/",
            "silver/foodfacts/",
            "gold/foodfacts/",
            "temp/",
        ]
        for p in prefixes:
            key = p if p.endswith("/") else p + "/"
            s3.put_object(Bucket=cfg["bucket"], Key=key)
            print(f"[bootstrap_minio] Préfixe assuré : s3://{cfg['bucket']}/{key}")

        # Vérification rapide pour s’assurer qu’on a bien accès
        listed = s3.list_objects_v2(Bucket=cfg["bucket"], Prefix="landing/foodfacts/", MaxKeys=1)
        print(f"[bootstrap_minio] Liste test OK. clés_trouvées={listed.get('KeyCount', 0)}")

        return {"endpoint": cfg["endpoint"], "bucket": cfg["bucket"], "prefixes": prefixes, "source": cfg["source"]}

    PythonOperator(
        task_id="ensure_minio_layout",
        python_callable=ensure_bucket_and_prefixes,
    )

# dags/etl_foodfacts_basic.py
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta

# Paramètres par défaut : peu de tentatives, exécution quotidienne, pas de backfill
default_args = {
    "owner": "data_team",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "depends_on_past": False,
}

with DAG(
    dag_id="etl_foodfacts_basic",
    description="Pipeline de test : création d’un CSV → nettoyage avec Spark → chargement dans DuckDB",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["etl", "spark", "duckdb", "minio", "toy"],
) as dag:

    # Petits marqueurs visuels pour le début et la fin du pipeline
    # (je pourrai les remplacer plus tard par des notifications ou des triggers)
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end", trigger_rule=TriggerRule.ALL_DONE)

    # 1) Extraction : création d’un petit CSV et envoi vers le dossier landing de MinIO
    extract = BashOperator(
        task_id="extract_create_csv_to_minio",
        bash_command="python /opt/airflow/jobs/extract.py --date {{ ds }}",
    )

    # 2) Transformation : Spark lit le CSV du landing, nettoie les données
    #    puis écrit le résultat dans la zone silver (fichiers cleaned.csv / part-*.csv)
    transform = BashOperator(
        task_id="transform_spark_minio_to_minio",
        bash_command="python /opt/airflow/jobs/transform_spark.py --date {{ ds }}",
    )

    # 3) Chargement : téléchargement des fichiers nettoyés (part-*.csv) depuis silver
    #    et insertion dans la table test_items de DuckDB
    load = BashOperator(
        task_id="load_silver_into_duckdb",
        bash_command="python /opt/airflow/jobs/load_duckdb.py --date {{ ds }}",
    )

    # Définition du flux d’exécution des tâches
    start >> extract >> transform >> load >> end

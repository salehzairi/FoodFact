from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    dag_id="bootstrap_duckdb",
    description="Idempotent : s’assure que le fichier DuckDB et une table simple existent",
    start_date=datetime(2025, 1, 1),
    schedule_interval="@once",
    catchup=False,
    tags=["infra", "duckdb", "bootstrap"],
) as dag:

    def ensure_duckdb_table():
        import duckdb, os
        db_path = "/opt/airflow/data/warehouse.duckdb"
        
        # Crée le dossier data s’il n’existe pas déjà (utile lors du premier lancement)
        os.makedirs("/opt/airflow/data", exist_ok=True)
        
        # Connexion (ou création automatique) de la base DuckDB
        con = duckdb.connect(db_path)
        
        # Je garde le schéma très simple, aligné avec les CSV nettoyés que je vais charger plus tard
        con.execute("""
            CREATE TABLE IF NOT EXISTS test_items (
                id INTEGER,
                name VARCHAR,
                qty INTEGER,
                ts DATE
            );
        """)
        
        # Fermeture propre de la connexion
        con.close()
        
        # Retourne quelques infos utiles pour les logs ou les tests
        return {"db_path": db_path, "table": "test_items"}

    # Tâche unique : vérifier/créer le fichier DuckDB et la table test_items
    PythonOperator(
        task_id="ensure_duckdb_table",
        python_callable=ensure_duckdb_table,
    )

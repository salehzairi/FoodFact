import argparse
from pyspark.sql import SparkSession, functions as F
from airflow.hooks.base import BaseHook

def _minio_cfg():
    """
    Récupère la configuration MinIO depuis la connexion Airflow `minio_default`,
    avec des valeurs par défaut au cas où la connexion n’existe pas.
    """
    try:
        c = BaseHook.get_connection("minio_default")
        e = c.extra_dejson or {}
        endpoint = (e.get("endpoint_url") or e.get("host") or "http://minio:9000").strip()
        bucket   = (e.get("bucket", "data")).strip()
        region   = (e.get("region_name", "us-east-1")).strip()
        access   = (c.login or "minio").strip()
        secret   = (c.password or "minio123").strip()
    except Exception:
        # Valeurs par défaut si la connexion n’est pas trouvée
        endpoint = "http://minio:9000"
        bucket   = "data"
        region   = "us-east-1"
        access   = "minio"
        secret   = "minio123"
    return dict(endpoint=endpoint, bucket=bucket, region=region, access=access, secret=secret)

def _spark(cfg: dict) -> SparkSession:
    """
    Initialise une session Spark configurée pour accéder à MinIO via S3A.

    Remarque : j’utilise ici `spark.jars.packages` pour télécharger
    les dépendances Hadoop AWS au moment de l’exécution. 
    Si le conteneur n’a pas Internet, il faudra plutôt les ajouter
    manuellement dans `/opt/spark/jars` et retirer cette ligne.
    """
    return (
        SparkSession.builder.appName("toy_transform")
        # Téléchargement des dépendances nécessaires à S3A (compatibles Spark 3.5.x)
        .config(
            "spark.jars.packages",
            "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262",
        )
        # Configuration pour MinIO
        .config("spark.hadoop.fs.s3a.endpoint", cfg["endpoint"])    # ex: http://minio:9000
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.access.key", cfg["access"])
        .config("spark.hadoop.fs.s3a.secret.key", cfg["secret"])
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        # Certaines configurations nécessitent la signature v4
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.hadoop.fs.s3a.signing-algorithm", "S3SignerType")
        .getOrCreate()
    )

def main(date_str: str):
    cfg = _minio_cfg()
    spark = _spark(cfg)

    src = f"s3a://{cfg['bucket']}/landing/foodfacts/{date_str}/raw.csv"
    dst = f"s3a://{cfg['bucket']}/silver/foodfacts/{date_str}/cleaned"

    # Lecture du fichier CSV brut depuis MinIO
    # Je demande à Spark d’inférer les types pour éviter des conversions manuelles
    df = (
        spark.read
             .option("header", True)
             .option("inferSchema", True)
             .csv(src)
    )

    # Sécurité : si certaines colonnes manquent dans le fichier, je les ajoute
    cols = df.columns
    if "id" not in cols:
        df = df.withColumn("id", F.lit(None).cast("int"))
    if "name" not in cols:
        df = df.withColumn("name", F.lit(None).cast("string"))
    if "qty" not in cols:
        df = df.withColumn("qty", F.lit(0).cast("int"))

    # Nettoyage de base : typage, formatage des noms, suppression des lignes invalides
    df_clean = (
        df.withColumn("id", F.col("id").cast("int"))
          .withColumn("name", F.when(F.col("name").isNotNull(), F.initcap(F.trim(F.col("name")))).otherwise(None))
          .withColumn("qty", F.col("qty").cast("int"))
          .filter(F.col("qty") > 0)
          .withColumn("ts", F.lit(date_str).cast("date"))
    )

    # Écriture du jeu de données nettoyé vers la zone silver dans MinIO
    # Spark crée un dossier contenant les part-*.csv et un fichier _SUCCESS
    (df_clean.coalesce(1)  # comme c’est un petit échantillon, je regroupe tout dans un seul fichier
            .write.mode("overwrite")
            .option("header", True)
            .csv(dst))

    spark.stop()
    print(f"[transform] jeu de données nettoyé écrit dans : {dst}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    main(args.date)

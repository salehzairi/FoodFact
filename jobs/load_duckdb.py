# jobs/load_duckdb.py (only the S3/DuckDB setup shown here)
import argparse
import duckdb
from urllib.parse import urlparse
from airflow.hooks.base import BaseHook

def _minio_cfg():
    try:
        c = BaseHook.get_connection("minio_default")
        e = c.extra_dejson or {}
        endpoint = (e.get("endpoint_url") or e.get("host") or "http://minio:9000").strip()
        bucket   = (e.get("bucket", "data")).strip()
        region   = (e.get("region_name", "us-east-1")).strip()
        access   = (c.login or "minio").strip()
        secret   = (c.password or "minio123").strip()
    except Exception:
        endpoint, bucket, region, access, secret = "http://minio:9000", "data", "us-east-1", "minio", "minio123"
    # --- normalize for DuckDB httpfs ---
    u = urlparse(endpoint)
    hostport = (u.netloc or u.path or endpoint).lstrip("/")  # supports "minio:9000" or "http://minio:9000"
    use_ssl = (u.scheme == "https")
    return dict(endpoint_raw=endpoint, hostport=hostport, use_ssl=use_ssl,
                bucket=bucket, region=region, access=access, secret=secret)

def main(date_str: str):
    cfg = _minio_cfg()
    con = duckdb.connect("/opt/airflow/data/warehouse.duckdb")

    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")

    # DuckDB S3 settings (no scheme in s3_endpoint!)
    con.execute("SET s3_region = ?;", [cfg["region"]])
    con.execute("SET s3_endpoint = ?;", [cfg["hostport"]])       # e.g. "minio:9000"
    con.execute("SET s3_url_style = 'path';")
    con.execute("SET s3_use_ssl = ?;", ["true" if cfg["use_ssl"] else "false"])
    con.execute("SET s3_access_key_id = ?;", [cfg["access"]])
    con.execute("SET s3_secret_access_key = ?;", [cfg["secret"]])

    src_glob = f"s3://{cfg['bucket']}/silver/foodfacts/{date_str}/cleaned/*.csv"

    con.execute("CREATE SCHEMA IF NOT EXISTS foodfacts;")
    con.execute("""
        CREATE TABLE IF NOT EXISTS foodfacts.cleaned (
            id   INTEGER,
            name TEXT,
            qty  INTEGER,
            ts   DATE
        );
    """)
    con.execute("DELETE FROM foodfacts.cleaned WHERE ts = CAST(? AS DATE);", [date_str])
    con.execute(f"""
        INSERT INTO foodfacts.cleaned
        SELECT
            TRY_CAST(id AS INTEGER)  AS id,
            name,
            TRY_CAST(qty AS INTEGER) AS qty,
            TRY_CAST(ts AS DATE)     AS ts
        FROM read_csv_auto('{src_glob}', header=true)
    """)

    cnt = con.execute("SELECT COUNT(*) FROM foodfacts.cleaned WHERE ts = CAST(? AS DATE)", [date_str]).fetchone()[0]
    print(f"[load] inserted {cnt} rows for {date_str} into DuckDB table foodfacts.cleaned")
    con.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    main(args.date)

# 🚀 Mise à jour rapide de l’environnement ETL
**(Airflow + MinIO + Spark + DuckDB)**

Salut 👋  
J’ai mis à jour les fichiers Docker avec toutes les dernières corrections.  
👉 Voici les étapes à suivre pour avoir **le même environnement local que moi** :

---

## 🧩 Étapes à suivre

### 1️⃣ Fermez vos conteneurs actuels
```bash
docker compose down
```

---

### 2️⃣ Remplacez les fichiers
Copiez mes nouvelles versions de :
- `docker-compose.yml`  
- `Makefile`  
- `containers/airflow/Dockerfile`  

(collez-les dans vos dossiers locaux du projet **openfoodfacts-mig8110**)

---

### 3️⃣ Placez les **DAGs** et les **scripts ETL**
> Ces répertoires sont montés dans les conteneurs par `docker-compose.yml`.

- **DAGs Airflow** → placez-les dans **`./dags/`**
  - `./dags/bootstrap_minio.py`
  - `./dags/etl_foodfacts_basic.py`

- **Scripts ETL** → placez-les dans **`./jobs/`**
  - `./jobs/extract.py`
  - `./jobs/transform_spark.py`
  - `./jobs/load_duckdb.py`

- (Les autres dossiers montés par défaut)  
  - `./data/` → entrepôt DuckDB et données locales  
  - `./logs/` → logs Airflow

> Si les dossiers n’existent pas localement, créez-les : `mkdir -p dags jobs data logs`

---

### 4️⃣ Nettoyez les anciens conteneurs et images
```bash
docker system prune -af
```

---

### 5️⃣ Rebuild complet
```bash
make up
```
> Equivalent à : `docker compose build && docker compose up airflow-init && docker compose up -d`

---

### 6️⃣ Vérifiez que tout fonctionne
- 🌬️ **Airflow** → <http://localhost:8080>  
- 🪣 **MinIO** → <http://localhost:9001>

Dans Airflow, vous devez voir les DAGs : `bootstrap_minio` et `etl_foodfacts_basic`.

---

## 💡 En cas de problème
Si vous avez encore des erreurs :

```bash
docker compose down -v
make up
```

---

✅ **Résultat attendu :**  
Vous aurez **exactement le même environnement que moi**, avec Spark, DuckDB et MinIO configurés et fonctionnels.

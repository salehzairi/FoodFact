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

### 3️⃣ Nettoyez les anciens conteneurs et images
```bash
docker system prune -af
```

---

### 4️⃣ Rebuild complet
```bash
make up
```

---

### 5️⃣ Vérifiez que tout fonctionne
- 🌬️ **Airflow** → [http://localhost:8080](http://localhost:8080)  
- 🪣 **MinIO** → [http://localhost:9001](http://localhost:9001)

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

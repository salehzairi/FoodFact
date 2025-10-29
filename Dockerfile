FROM apache/airflow:2.9.2

# ---- Python deps first (your requirements should include: boto3, duckdb, pyspark) ----
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt

# ---- Quarto (unchanged) ----
COPY quarto.sh /
RUN cd / && bash /quarto.sh

# If you use setup_conn.py at build-time, better copy it but run it at container start (or via your Make target)
COPY setup_conn.py $AIRFLOW_HOME/

# ---- System deps Spark needs: Java, ps, curl, certs ----
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      default-jdk \
      procps \
      curl \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ---- Spark 3.5.1 (Hadoop 3) ----
RUN curl -fsSL https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz -o /tmp/spark.tgz && \
    mkdir -p /opt/spark && \
    tar -xzf /tmp/spark.tgz -C /opt/spark --strip-components=1 && \
    rm -f /tmp/spark.tgz

# ---- Environment for Java & Spark ----
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_HOME=/opt/spark
ENV PATH="${JAVA_HOME}/bin:${SPARK_HOME}/bin:${SPARK_HOME}/sbin:${PATH}"

# (Optional but useful) Make PySpark available even if pip pyspark isn't installed
# ENV PYTHONPATH="${SPARK_HOME}/python:${SPARK_HOME}/python/lib/py4j-src.zip:${PYTHONPATH}"
# Make Spark’s Python bindings visible to PySpark
ENV PYTHONPATH="/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip:${PYTHONPATH}"

# Return to airflow user (Airflow expects to run as this user)
USER airflow

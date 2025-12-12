

### How It Works
 - Postgres → Airflow metadata DB
 - Mongo → Your DAG will store press releases here
 - Airflow container → Loads your DAGs from ./dags/
 - Starts webserver + scheduler automatically
 - Admin user created automatically

### Run Docker-Compose
```bash

# open terminal 1
docker-compose down && docker-compose up ---build -d

# check logs
# open terminal 2
docker-compose logs -f airflow-webserver

# open terminal 3
docker-compose logs -f airflow-scheduler

# stop and remove
docker-compose down -v

# retrieve IP address
docker inspect <CONTAINER_ID>
```

```bash
# access Airflow UI
http://localhost:8080
username=admin
password=admin

# enter connection credentials for postgres
host=airflow_postgres_1
port=5432
login=airflow
password=airflow
schema=airflow
```
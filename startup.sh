apt-get update &
apt-get install -y wkhtmltopdf &

wait

uvicorn initialize:app --host 0.0.0.0 --port 8000

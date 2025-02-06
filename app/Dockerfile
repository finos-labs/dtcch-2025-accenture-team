FROM public.ecr.aws/docker/library/python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .
COPY chat chat/
COPY processed_files processed_files/
COPY summary summary/
COPY controls_mapping controls_mapping/
COPY send_email send_email/

EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "2400", "main:app"]

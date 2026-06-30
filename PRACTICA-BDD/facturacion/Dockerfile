FROM python:3.11
RUN pip install psycopg2-binary -i https://pypi.tuna.tsinghua.edu.cn/simple --retries 5 --timeout 300
WORKDIR /app
COPY participante_facturacion.py .
CMD ["python", "-u", "participante_facturacion.py"]

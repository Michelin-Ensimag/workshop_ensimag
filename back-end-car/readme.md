# Backend car


```
python3 -m venv venv
source ./venv/bin/activate

pip install opentelemetry-distro
pip install opentelemetry-exporter-otlp
pip install opentelemetry-exporter-otlp-proto
pip install opentelemetry-sdk
pip install opentelemetry-instrumentation


opentelemetry-bootstrap -a install

opentelemetry-instrument \
    --traces_exporter otlp \
    --metrics_exporter otlp \
    --logs_exporter console \
    --service_name "backend-car" \
    --exporter_otlp_endpoint "http://localhost:4242" \
    --exporter_otlp_protocol "http/protobuf" \
    python3 ./backend_car.py
```

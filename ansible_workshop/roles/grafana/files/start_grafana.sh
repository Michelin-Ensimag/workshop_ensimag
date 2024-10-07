CONF_FILE="/etc/grafana/grafana.ini"
LOG_DIR="/var/log/grafana"
DATA_DIR="/var/lib/grafana"
PLUGINS_DIR="/var/lib/grafana/plugins"
PROVISIONING_CFG_DIR="/etc/grafana/provisioning"

/usr/share/grafana/bin/grafana server --homepath "/usr/share/grafana" --config=$CONF_FILE --pidfile=$PID_FILE_DIR/grafana-server.pid --packaging=deb cfg:default.paths.logs=$LOG_DIR cfg:default.paths.data=$DATA_DIR cfg:default.paths.plugins=$PLUGINS_DIR cfg:default.paths.provisioning=$PROVISIONING_CFG_DIR
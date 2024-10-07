# Ansible workshop

Use this in a container with workshop_image !

Run the observability playbook: `ansible-playbook -i inventories/prod playbooks/install_observability.yml`

In other shells, launch all layers with appropriate startup scripts (in `/scripts` folder), the good order is:

- otelcol
- prometheus
- grafana

Test connection to grafana: `http://localhost:3000`
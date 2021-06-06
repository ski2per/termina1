# Hosts generate code for Ansible(Not used currently)
import json
import requests

GRU_HOST = 'http://localhost:8000'
#ANSIBLE_HOSTS_FILE = '/etc/ansible/hosts'
ANSIBLE_HOSTS_FILE = 'hosts'

response = requests.get(f'{GRU_HOST}/genhosts')
if response.status_code == 200:
    hosts = json.loads(response.text)
    with open(ANSIBLE_HOSTS_FILE, "w") as f:
        f.write('[default]\n')
        for host in hosts:
            line = f'{host["name"]} ansible_ssh_host=127.0.0.1 ansible_port={host["port"]} internal_ip={host["ip"]}\n'
            f.write(f'{line}')
else:
    print(f"Error while getting hosts: {response}")

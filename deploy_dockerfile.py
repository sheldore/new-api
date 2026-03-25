"""Quick deploy Neo-API Dockerfile and build."""
import os
import paramiko

HOST = '8.130.94.182'
USER = 'root'
KEY_FILE = '/c/Users/sheld/PycharmProjects/dreamfac/阿里云secret_key.pem'
REMOTE_DIR = '/opt/neo-api'

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=KEY_FILE, timeout=15)
    return client

client = connect()
sftp = client.open_sftp()

# Upload Dockerfile
print('Uploading Dockerfile...')
sftp.put('/c/Users/sheld/PycharmProjects/dreamfac/neo-api/Dockerfile', f'{REMOTE_DIR}/Dockerfile')

# Build
print('Building...')
stdin, stdout, stderr = client.exec_command(f'cd {REMOTE_DIR} && DOCKER_BUILDKIT=1 docker build -t neo-api:dreamfac --platform linux/amd64 . 2>&1', timeout=1800)

for line in stdout:
    print(line.strip())

exit_code = stdout.channel.recv_exit_status()
print(f'Build exit code: {exit_code}')

if exit_code == 0:
    print('Starting container...')
    cmd = """docker stop neo-api 2>/dev/null || true; docker rm neo-api 2>/dev/null || true; docker run -d --name neo-api --network dreamfac-net -p 3000:3000 -v neo-api-data:/data -e TZ=Asia/Shanghai --restart unless-stopped neo-api:dreamfac && echo 'Container started' && sleep 5 && docker ps --filter name=neo-api"""
    _, stdout, _ = client.exec_command(cmd)
    print(stdout.read().decode())

sftp.close()
client.close()
print('Done')

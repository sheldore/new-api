"""Deploy Neo-API to 8.130.94.182:3000 from a prebuilt Docker artifact."""
import os
import sys
import time

import paramiko

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HOST = '8.130.94.182'
USER = 'root'
KEY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'secret_key.pem',
)
REMOTE_DIR = '/opt/neo-api'
DEPLOY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEPLOY_DIR)
ARTIFACT_NAME = 'neo-api-dreamfac.tar.gz'
LOADED_IMAGE = 'ghcr.io/sheldore/new-api:dreamfac'
COMPOSE_FILE = 'docker-compose.prod.yml'


def resolve_artifact_path():
    candidates = []
    if len(sys.argv) > 1:
        candidates.append(sys.argv[1])
    candidates.extend([
        os.path.join(PROJECT_ROOT, ARTIFACT_NAME),
        os.path.join(os.getcwd(), ARTIFACT_NAME),
    ])

    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)

    print(f'❌ Docker artifact not found: {ARTIFACT_NAME}')
    print('Usage: python deploy/deploy.py /path/to/neo-api-dreamfac.tar.gz')
    sys.exit(1)


def connect():
    if not os.path.exists(KEY_FILE):
        print(f'❌ SSH key not found: {KEY_FILE}')
        sys.exit(1)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=KEY_FILE, timeout=15)
    return client


def run_remote(client, cmd, timeout=600):
    display = cmd.strip().split('\n')[0][:100]
    print(f'\n>>> {display}...')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        print(out[-3000:] if len(out) > 3000 else out)
    if exit_code != 0:
        print(f'STDERR: {err[-2000:]}')
        print(f'Exit code: {exit_code}')
    return exit_code, out, err


def wait_for_status(client, url, attempts=24, delay=5):
    for _ in range(attempts):
        _, stdout, _ = client.exec_command(
            f'curl -s -o /dev/null -w "%{{http_code}}" {url} 2>/dev/null || echo "000"'
        )
        status = stdout.read().decode().strip()
        if status in ('200', '302'):
            return status
        time.sleep(delay)
    return status


def main():
    artifact_path = resolve_artifact_path()
    compose_path = os.path.join(DEPLOY_DIR, COMPOSE_FILE)
    artifact_size_mb = os.path.getsize(artifact_path) / (1024 * 1024)

    print('=' * 55)
    print('  Neo-API Deploy to 8.130.94.182:3000')
    print('=' * 55)

    print('\n[1/5] Checking local artifact...')
    print(f'Artifact: {artifact_path}')
    print(f'Size: {artifact_size_mb:.1f} MB')

    print('\n[2/5] Connecting to server...')
    client = connect()

    print('\n[3/5] Uploading artifact and compose file...')
    run_remote(client, f'mkdir -p {REMOTE_DIR}/deploy')

    sftp = client.open_sftp()
    remote_artifact = f'{REMOTE_DIR}/{ARTIFACT_NAME}'
    remote_compose = f'{REMOTE_DIR}/deploy/{COMPOSE_FILE}'
    sftp.put(artifact_path, remote_artifact)
    sftp.put(compose_path, remote_compose)
    print(f'Uploaded {ARTIFACT_NAME}')
    print(f'Uploaded {COMPOSE_FILE}')

    print('\n[4/5] Loading image and restarting services...')
    deploy_exit_code, _, _ = run_remote(client, f'''
set -e
mkdir -p {REMOTE_DIR}/deploy
cd {REMOTE_DIR}
docker network create dreamfac-net 2>/dev/null || true
gzip -dc {ARTIFACT_NAME} | docker load
cd {REMOTE_DIR}/deploy
docker compose -f {COMPOSE_FILE} down --remove-orphans 2>/dev/null || true
docker compose -f {COMPOSE_FILE} up -d
''', timeout=1800)
    if deploy_exit_code != 0:
        sftp.close()
        client.close()
        sys.exit(deploy_exit_code)

    print('\n[5/5] Verifying deployment...')
    verify_exit_code, _, _ = run_remote(client, f'''
cd {REMOTE_DIR}/deploy
docker compose -f {COMPOSE_FILE} ps
echo ""
echo "=== App logs ==="
docker compose -f {COMPOSE_FILE} logs new-api --tail 30 2>/dev/null || true
''')
    if verify_exit_code != 0:
        sftp.close()
        client.close()
        sys.exit(verify_exit_code)

    status = wait_for_status(client, 'http://localhost:3000/api/status')

    if status in ('200', '302'):
        print('\n' + '=' * 55)
        print('  DEPLOY SUCCESS!')
        print(f'  http://{HOST}:3000')
        print('=' * 55)
    else:
        print(f'\nApp returned HTTP {status} - may still be starting.')
        print(
            f'Check: ssh -i <key> root@{HOST} '
            f'"cd {REMOTE_DIR}/deploy && docker compose -f {COMPOSE_FILE} logs"'
        )

    sftp.close()
    client.close()


if __name__ == '__main__':
    main()

"""Deploy Neo-API to 8.130.94.182:3000."""
import os
import sys
import time
import tarfile
import paramiko
from io import BytesIO

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HOST = '8.130.94.182'
USER = 'root'
KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '阿里云secret_key.pem')
REMOTE_DIR = '/opt/neo-api'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.next', '.venv', 'venv',
    'uploads', '.claude', 'openspec', 'web/node_modules',
}
EXCLUDE_FILES = {'.env.local', '.DS_Store', 'Thumbs.db', 'new-api'}
EXCLUDE_EXTS = {'.pyc', '.pyo', '.log'}


def should_include(path, name):
    if name in EXCLUDE_DIRS or name in EXCLUDE_FILES:
        return False
    _, ext = os.path.splitext(name)
    if ext in EXCLUDE_EXTS:
        return False
    return True


def create_tarball(project_root):
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if should_include(root, d)]
            for f in files:
                if not should_include(root, f):
                    continue
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, project_root)
                try:
                    tar.add(full_path, arcname=arcname)
                except (PermissionError, FileNotFoundError):
                    pass
    buf.seek(0)
    size_mb = buf.getbuffer().nbytes / (1024 * 1024)
    print(f'Tarball created: {size_mb:.1f} MB')
    return buf


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
    return exit_code


def main():
    print('=' * 55)
    print('  Neo-API Deploy to 8.130.94.182:3000')
    print('=' * 55)

    # Step 1: Create tarball
    print('\n[1/5] Creating project tarball...')
    tarball = create_tarball(PROJECT_ROOT)

    # Step 2: Connect via SSH key
    print('\n[2/5] Connecting to server...')
    client = connect()

    # Configure Docker mirror (Alibaba Cloud)
    run_remote(client, """
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com"
  ]
}
EOF
systemctl daemon-reload
systemctl restart docker
echo 'Docker mirror configured'
""")

    # Step 3: Upload tarball
    print('\n[3/5] Uploading project...')
    run_remote(client, f'mkdir -p {REMOTE_DIR}')

    sftp = client.open_sftp()
    remote_tar = f'{REMOTE_DIR}/project.tar.gz'
    with sftp.file(remote_tar, 'wb') as f:
        f.set_pipelined(True)
        data = tarball.read()
        f.write(data)
    print(f'Uploaded {len(data) / (1024 * 1024):.1f} MB')

    # Step 4: Extract
    print('\n[4/5] Extracting...')
    run_remote(client, f"""
set -e
cd {REMOTE_DIR}
tar xzf project.tar.gz
rm project.tar.gz
ls -la deploy/
""")

    # Step 5: Docker Compose build + up
    print('\n[5/5] Building and starting services...')

    run_remote(client, f"""
cd {REMOTE_DIR}/deploy

# Ensure external network exists
docker network create dreamfac-net 2>/dev/null || true

# Ensure external volumes exist
docker volume create deploy_minidrama_pgdata 2>/dev/null || true
docker volume create deploy_minidrama_minio 2>/dev/null || true

docker compose down --remove-orphans 2>/dev/null || true

nohup bash -c '
  set -e
  cd {REMOTE_DIR}/deploy
  docker compose build 2>&1
  docker compose up -d 2>&1
  echo "DEPLOY_DONE"
' > /tmp/neoapi_build.log 2>&1 &

echo "Build started in background (PID: $!)"
echo "Log: /tmp/neoapi_build.log"
""")

    # Poll build progress
    print('\nWaiting for build to complete (this may take 15-30 minutes)...')
    for i in range(120):  # 60 minutes max
        time.sleep(30)
        _, stdout, _ = client.exec_command('tail -5 /tmp/neoapi_build.log 2>/dev/null')
        tail = stdout.read().decode('utf-8', errors='replace').strip()
        last_line = tail.split('\n')[-1][:100] if tail else '...'
        print(f'  [{(i+1)*30}s] {last_line}')

        if 'DEPLOY_DONE' in tail:
            print('\nBuild complete!')
            break
    else:
        print('\nBuild timed out after 60 minutes')

    # Check result
    time.sleep(10)
    run_remote(client, f"""
cd {REMOTE_DIR}/deploy
docker compose ps
echo ""
echo "=== Last 30 lines of build log ==="
tail -30 /tmp/neoapi_build.log
echo ""
echo "=== App logs ==="
docker compose logs new-api --tail 15 2>/dev/null || true
""")

    # Verify app is responding
    _, stdout, _ = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/status 2>/dev/null || echo "000"')
    status = stdout.read().decode().strip()

    if status in ('200', '302'):
        print('\n' + '=' * 55)
        print('  DEPLOY SUCCESS!')
        print(f'  http://{HOST}:3000')
        print('=' * 55)
    else:
        print(f'\nApp returned HTTP {status} - may still be starting.')
        print(f'Check: ssh -i <key> root@{HOST} "cd {REMOTE_DIR}/deploy && docker compose logs"')

    sftp.close()
    client.close()


if __name__ == '__main__':
    main()

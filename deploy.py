"""Deploy Neo-API to server by uploading source and building remotely."""
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
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '阿里云secret_key.pem')
REMOTE_DIR = '/opt/neo-api'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDE_DIRS = {
    '.git', '.cursor', 'node_modules', 'dist', '.next',
    '__pycache__', '.venv', 'venv', 'uploads',
}
EXCLUDE_FILES = {'.env', '.env.local', '.DS_Store', 'Thumbs.db', '.dockerignore'}
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


def run_remote(client, cmd, timeout=1800):
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
    print('\n[1/4] Creating project tarball...')
    tarball = create_tarball(PROJECT_ROOT)

    # Step 2: Connect
    print('\n[2/4] Connecting to server...')
    client = connect()

    # Step 3: Upload
    print('\n[3/4] Uploading source code...')
    run_remote(client, f'mkdir -p {REMOTE_DIR} && rm -rf {REMOTE_DIR}/*')

    sftp = client.open_sftp()
    remote_tar = f'{REMOTE_DIR}/project.tar.gz'
    with sftp.file(remote_tar, 'wb') as f:
        f.set_pipelined(True)
        data = tarball.read()
        f.write(data)
    print(f'Uploaded {len(data) / (1024 * 1024):.1f} MB')

    # Step 4: Extract and build
    print('\n[4/4] Extracting and building...')
    run_remote(client, f"""
set -e
cd {REMOTE_DIR}
tar xzf project.tar.gz
rm project.tar.gz

# Ensure network exists
docker network create dreamfac-net 2>/dev/null || true

# Build with Docker
echo 'Building Neo-API Docker image...'
DOCKER_BUILDKIT=1 docker build -t neo-api:dreamfac --platform linux/amd64 . 2>&1

echo 'Stopping old container...'
docker stop neo-api 2>/dev/null || true
docker rm neo-api 2>/dev/null || true

echo 'Starting new container...'
docker run -d \\
  --name neo-api \\
  --network dreamfac-net \\
  -p 3000:3000 \\
  -v neo-api-data:/data \\
  -e TZ=Asia/Shanghai \\
  --restart unless-stopped \\
  neo-api:dreamfac

echo 'BUILD_DONE'
""")

    # Wait and check
    print('\nWaiting for container to start...')
    time.sleep(10)

    run_remote(client, """
docker ps --filter name=neo-api --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'
echo ""
echo "=== Recent logs ==="
docker logs neo-api --tail 20 2>&1 || true
""")

    # Health check
    _, stdout, _ = client.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null || echo "000"')
    status = stdout.read().decode().strip()

    if status in ('200', '302', '307'):
        print('\n' + '=' * 55)
        print('  DEPLOY SUCCESS!')
        print(f'  http://{HOST}:3000')
        print('=' * 55)
    else:
        print(f'\nApp returned HTTP {status} - may still be starting.')
        print(f'Check logs: ssh -i <key> root@{HOST} "docker logs neo-api -f"')

    sftp.close()
    client.close()


if __name__ == '__main__':
    main()

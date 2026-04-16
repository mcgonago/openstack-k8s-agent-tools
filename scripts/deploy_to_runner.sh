#!/bin/bash
set -euo pipefail

# K8s Agent Tools Server — Deploy to 10.0.151.101
# Following the isdlc-server 9-step deploy pattern.

REMOTE_HOST="ospng@10.0.151.101"
SSH_KEY="$HOME/.ssh/id_rsa_omcgonag_runner"
SSH_OPTS="-i $SSH_KEY"
REMOTE_BASE="/home/ospng/k8s-agent-tools-server"
REMOTE_APP="$REMOTE_BASE/app"
REMOTE_PLUGIN="$REMOTE_BASE/plugin"
REMOTE_VENV="$REMOTE_BASE/venv"
REMOTE_DATA="$REMOTE_BASE/data"
REMOTE_BACKUPS="$REMOTE_BASE/backups"

LOCAL_SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
LOCAL_REPO="$(dirname "$LOCAL_SCRIPTS")"

SERVICE_NAME="k8s-agent-tools-server"

echo "============================================"
echo "  K8s Agent Tools Server -- Deploy"
echo "  Target: $REMOTE_HOST"
echo "  Remote: $REMOTE_BASE"
echo "============================================"
echo

# --- Step 1: Stop service ---
echo "[Step 1/9] Stopping service..."
ssh $SSH_OPTS "$REMOTE_HOST" "sudo systemctl stop $SERVICE_NAME 2>/dev/null || true"
echo "  Done."
echo

# --- Step 2: Create remote directories ---
echo "[Step 2/9] Creating remote directories..."
ssh $SSH_OPTS "$REMOTE_HOST" "mkdir -p $REMOTE_APP $REMOTE_PLUGIN $REMOTE_DATA $REMOTE_BACKUPS"
echo "  Done."
echo

# --- Step 3: rsync web_app/ code ---
echo "[Step 3/9] Syncing application code..."
rsync -avz --delete -e "ssh $SSH_OPTS" \
    "$LOCAL_SCRIPTS/web_app/" \
    "$REMOTE_HOST:$REMOTE_APP/web_app/"

rsync -avz -e "ssh $SSH_OPTS" \
    "$LOCAL_SCRIPTS/run.py" \
    "$LOCAL_SCRIPTS/create_admin.py" \
    "$LOCAL_SCRIPTS/requirements.txt" \
    "$REMOTE_HOST:$REMOTE_APP/"
echo "  Done."
echo

# --- Step 4: rsync plugin repo ---
echo "[Step 4/9] Syncing plugin repo..."
rsync -avz --delete -e "ssh $SSH_OPTS" \
    --exclude='.git' \
    --exclude='scripts/data' \
    --exclude='scripts/web_app' \
    --exclude='__pycache__' \
    "$LOCAL_REPO/" \
    "$REMOTE_HOST:$REMOTE_PLUGIN/"
echo "  Done."
echo

# --- Step 5: Create/update venv + pip install ---
echo "[Step 5/9] Setting up Python venv..."
ssh $SSH_OPTS "$REMOTE_HOST" bash -s <<'VENV_EOF'
cd /home/ospng/k8s-agent-tools-server
if [ ! -d venv ]; then
    python3 -m venv venv
fi
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r app/requirements.txt
venv/bin/pip install --quiet gunicorn
VENV_EOF
echo "  Done."
echo

# --- Step 6: Seed data (first deploy only) ---
echo "[Step 6/9] Checking data directory..."
ssh $SSH_OPTS "$REMOTE_HOST" bash -s <<'SEED_EOF'
DATA_DIR=/home/ospng/k8s-agent-tools-server/data
if [ ! -f "$DATA_DIR/users.yaml" ]; then
    echo "  First deploy -- seeding data structure..."
    mkdir -p "$DATA_DIR/users" "$DATA_DIR/executions" "$DATA_DIR/analyses" \
             "$DATA_DIR/history" "$DATA_DIR/reports" "$DATA_DIR/cache"
    cat > "$DATA_DIR/config.yaml" <<'YAML'
operators:
  - glance-operator
  - nova-operator
  - heat-operator
  - horizon-operator
  - cinder-operator
  - manila-operator
  - neutron-operator
  - keystone-operator
integrations:
  jira_url: https://issues.redhat.com
  github_org: openstack-k8s-operators
  gerrit_url: https://review.opendev.org
YAML
    echo "  Data seeded. Run create_admin.py to create first user."
else
    echo "  Data directory exists -- skipping seed."
fi
SEED_EOF
echo "  Done."
echo

# --- Step 7: Install systemd + Apache configs ---
echo "[Step 7/9] Installing systemd and Apache configs..."
SYSTEMD_DIR="$(dirname "$LOCAL_SCRIPTS")/systemd"

scp $SSH_OPTS "$SYSTEMD_DIR/$SERVICE_NAME.service" "$REMOTE_HOST:/tmp/"
scp $SSH_OPTS "$SYSTEMD_DIR/$SERVICE_NAME-apache.conf" "$REMOTE_HOST:/tmp/"
scp $SSH_OPTS "$SYSTEMD_DIR/$SERVICE_NAME-backup.service" "$REMOTE_HOST:/tmp/"
scp $SSH_OPTS "$SYSTEMD_DIR/$SERVICE_NAME-backup.timer" "$REMOTE_HOST:/tmp/"

ssh $SSH_OPTS "$REMOTE_HOST" bash -s <<'INSTALL_EOF'
sudo cp /tmp/k8s-agent-tools-server.service /etc/systemd/system/
sudo cp /tmp/k8s-agent-tools-server-apache.conf /etc/httpd/conf.d/
sudo cp /tmp/k8s-agent-tools-server-backup.service /etc/systemd/system/
sudo cp /tmp/k8s-agent-tools-server-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
rm -f /tmp/k8s-agent-tools-server*
INSTALL_EOF
echo "  Done."
echo

# --- Step 8: SELinux + backup timer ---
echo "[Step 8/9] Configuring SELinux and backup timer..."
ssh $SSH_OPTS "$REMOTE_HOST" bash -s <<'SELINUX_EOF'
sudo semanage port -a -t http_port_t -p tcp 8087 2>/dev/null || true
sudo semanage port -a -t http_port_t -p tcp 5005 2>/dev/null || true
sudo setsebool -P httpd_can_network_connect 1 2>/dev/null || true
sudo chcon -Rt bin_t /home/ospng/k8s-agent-tools-server/venv/bin/ 2>/dev/null || true

sudo systemctl enable k8s-agent-tools-server-backup.timer
sudo systemctl start k8s-agent-tools-server-backup.timer
SELINUX_EOF
echo "  Done."
echo

# --- Step 9: Start service + verify ---
echo "[Step 9/9] Starting service and verifying..."
ssh $SSH_OPTS "$REMOTE_HOST" bash -s <<'START_EOF'
sudo systemctl enable k8s-agent-tools-server
sudo systemctl start k8s-agent-tools-server
sleep 2

echo "  Service status:"
sudo systemctl is-active k8s-agent-tools-server

echo "  Health check (direct):"
curl -sf http://127.0.0.1:5005/api/health || echo "  FAILED: direct health check"

echo "  Health check (via Apache):"
curl -sf http://10.0.151.101:8087/api/health || echo "  FAILED: Apache proxy health check"

sudo systemctl reload httpd 2>/dev/null || sudo systemctl restart httpd
START_EOF

echo
echo "============================================"
echo "  Deploy complete!"
echo "  URL: http://10.0.151.101:8087/"
echo "============================================"

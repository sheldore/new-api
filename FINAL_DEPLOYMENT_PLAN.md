# new-api 项目在已有项目环境中的部署方案

## 1. 部署方案概述

根据您的需求，我制定了一个在已有项目环境下部署 new-api 项目的完整方案，该方案将：

- 使用不同端口（3001）避免与现有项目冲突
- 在独立目录(/opt/new-api)中部署，不影响原项目
- 提供完整的配置和启动脚本
- 确保安全性和可维护性

## 2. 核心部署要点

### 2.1 端口规划
- 新项目使用端口 3001（避免与现有项目冲突）
- 现有项目继续使用其原有端口

### 2.2 目录结构
- 项目根目录：`/opt/new-api`
- 数据目录：`/opt/new-api/data`
- 日志目录：`/opt/new-api/logs`

### 2.3 配置文件
- `.env` 文件包含所有环境变量配置
- 启动脚本 `start-new-api.sh` 自动设置环境变量并启动程序
- systemd 服务文件（可选）用于自动启动和管理

## 3. 部署步骤摘要

### 步骤1：创建目录结构
```bash
mkdir -p /opt/new-api/data /opt/new-api/logs
```

### 步骤2：上传项目文件
将 new-api 项目的所有文件上传到 `/opt/new-api` 目录

### 步骤3：编译程序
```bash
cd /opt/new-api
go build -o new-api main.go
chmod +x new-api
```

### 步骤4：配置环境变量
创建 `.env` 文件并设置必要的配置项

### 步骤5：创建启动脚本
```bash
cat > /opt/new-api/start-new-api.sh << 'EOF'
#!/bin/bash
cd /opt/new-api
export PORT=3001
export LOG_DIR=/opt/new-api/logs
export SESSION_SECRET="your_strong_random_secret_here"
export TZ=Asia/Shanghai
export MEMORY_CACHE_ENABLED=true
export ERROR_LOG_ENABLED=true
mkdir -p $LOG_DIR
./new-api
EOF
chmod +x /opt/new-api/start-new-api.sh
```

### 步骤6：启动服务
```bash
# 直接运行
/opt/new-api/start-new-api.sh

# 或者使用systemd服务（推荐）
systemctl daemon-reload
systemctl enable new-api.service
systemctl start new-api.service
```

## 4. 关键配置说明

### 环境变量配置
- `PORT=3001` - 避免与现有项目冲突
- `SESSION_SECRET` - 必须设置为强随机字符串
- `SQL_DSN` - 数据库连接字符串（推荐使用SQLite）
- `REDIS_CONN_STRING` - Redis连接字符串（如果需要缓存）

### 目录权限
- 确保 `/opt/new-api` 目录对运行用户有读写权限
- 数据和日志目录需要有适当的权限设置

## 5. 验证部署

启动后可以通过以下方式验证部署：

```bash
# 检查端口监听
netstat -tlnp | grep :3001

# 查看进程
ps aux | grep new-api

# 查看日志
tail -f /opt/new-api/logs/*.log
```

项目将在 `http://服务器IP:3001` 上可用。

## 6. 后续维护

- 定期备份数据目录中的数据库文件
- 监控日志文件以排查问题
- 如需更新，只需重新编译并重启服务
- 可以使用 systemd 管理服务生命周期

这个方案确保了新项目与现有项目完全隔离，不会产生任何冲突，同时保证了新项目的稳定运行。
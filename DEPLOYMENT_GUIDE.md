# new-api 项目部署指南

## 1. 部署概述

本指南将指导您在已有项目环境中部署 new-api 项目，避免端口和资源冲突。

## 2. 部署前准备

### 2.1 获取项目文件
将项目源码上传到服务器的 `/opt/new-api` 目录中：

```bash
# 在服务器上创建目录
mkdir -p /opt/new-api

# 将项目文件上传到该目录
# 注意：需要确保有适当的权限来执行文件
```

### 2.2 安装依赖
确保服务器上安装了以下依赖：
- Go 1.22+
- Redis (如果使用Redis缓存)
- 数据库 (SQLite/MySQL/PostgreSQL)

## 3. 配置文件准备

### 3.1 创建环境变量文件
创建 `.env` 文件用于配置应用程序：

```bash
# 创建环境变量文件
cat > /opt/new-api/.env << EOF
# 端口配置
PORT=3001
TZ=Asia/Shanghai

# 会话密钥（请替换为强密码）
SESSION_SECRET=your_strong_random_secret_here

# 数据库配置（使用SQLite）
SQL_DSN=sqlite:///opt/new-api/data/new-api.db

# Redis配置（如果使用Redis缓存）
REDIS_CONN_STRING=redis://localhost:6379/0

# 功能开关
MEMORY_CACHE_ENABLED=true
ERROR_LOG_ENABLED=true
BATCH_UPDATE_ENABLED=true
EOF
```

### 3.2 创建数据目录
```bash
mkdir -p /opt/new-api/data /opt/new-api/logs
chmod 755 /opt/new-api/data /opt/new-api/logs
```

## 4. 启动脚本配置

### 4.1 创建启动脚本
创建 `/opt/new-api/start-new-api.sh`：

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

### 4.2 创建systemd服务（可选）
创建 `/etc/systemd/system/new-api.service`：

```bash
cat > /etc/systemd/system/new-api.service << 'EOF'
[Unit]
Description=New API Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/new-api
ExecStart=/opt/new-api/start-new-api.sh
Restart=always
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF
```

## 5. 编译和部署

### 5.1 编译Go程序
如果还没有编译好的程序，需要先编译：

```bash
cd /opt/new-api
go build -o new-api main.go
chmod +x new-api
```

### 5.2 启动服务
使用systemd启动服务（推荐）：

```bash
systemctl daemon-reload
systemctl enable new-api.service
systemctl start new-api.service
systemctl status new-api.service
```

或者直接运行：

```bash
cd /opt/new-api
./start-new-api.sh
```

## 6. 验证部署

### 6.1 检查服务状态
```bash
# 检查服务是否运行
systemctl status new-api.service

# 或者检查端口是否监听
netstat -tlnp | grep :3001
```

### 6.2 访问应用
访问 `http://服务器IP:3001` 来验证应用是否正常运行。

## 7. 故障排除

### 7.1 常见问题
1. **端口占用**：确保端口3001没有被其他程序占用
2. **权限问题**：确保程序和数据目录有适当权限
3. **数据库连接**：检查数据库配置是否正确
4. **Redis连接**：如果使用Redis，确保Redis服务正在运行

### 7.2 查看日志
```bash
# 查看服务日志
journalctl -u new-api.service -f

# 查看应用日志
tail -f /opt/new-api/logs/*.log
```

## 8. 配置说明

### 8.1 环境变量说明
- `PORT`: 应用监听端口，默认3001
- `SESSION_SECRET`: 会话加密密钥，必须是唯一的强密码
- `SQL_DSN`: 数据库连接字符串
- `REDIS_CONN_STRING`: Redis连接字符串
- `MEMORY_CACHE_ENABLED`: 是否启用内存缓存
- `ERROR_LOG_ENABLED`: 是否启用错误日志记录

## 9. 后续维护

### 9.1 更新应用
```bash
# 下载新版本代码
cd /opt/new-api
git pull origin main

# 重新编译
go build -o new-api main.go

# 重启服务
systemctl restart new-api.service
```

### 9.2 备份数据
```bash
# 备份数据库
cp /opt/new-api/data/new-api.db /backup/new-api-db-$(date +%Y%m%d).db
```
# new-api 项目在已有项目环境中的部署方案

> 已弃用：本文档记录的是旧的主机部署 / systemd 方案，不再作为当前有效部署入口。
>
> 当前在用的部署链路：
> - `deploy/deploy.py`
> - `deploy/docker-compose.prod.yml`
> - GitHub Actions 产物 `neo-api-dreamfac.tar.gz`
> - 服务器目录 `/opt/neo-api`
>
> 当前推荐执行方式：
>
> ```bash
> python deploy/deploy.py /path/to/neo-api-dreamfac.tar.gz
> ```
>
> 说明：为避免继续把人引导到旧的源码上传、服务器编译、`start-new-api.sh` 或 `new-api.service` 流程，下面旧方案内容已移除。

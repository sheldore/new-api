# new-api 项目部署指南

> 已弃用：本文档描述的是旧的源码上传 / 服务器编译 / systemd 部署流程，不再作为当前有效部署入口。
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
> 说明：为避免误用，下面旧流程内容已移除。如需查看当前部署实现，请直接以 `deploy/deploy.py` 和 `deploy/docker-compose.prod.yml` 为准。

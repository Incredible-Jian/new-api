# 本地 API 供应测试环境

从仓库根目录运行以下命令。需要 Docker Compose 和 Python 3.10+。仅首次初始化运行第一行，已有本地密码文件会受到独占创建保护。

```powershell
python deploy/local/init_env.py
docker compose -f deploy/local/compose.yaml up --build -d --wait
python -B deploy/local/bootstrap.py
python -B deploy/local/smoke.py
python -B deploy/local/check_isolation.py
./deploy/local/check-restore.ps1
```

控制台位于 http://127.0.0.1:33080 。管理员为 pilotadmin，密码由 deploy/local/.env 中的 LOCAL_ADMIN_PASSWORD 提供。本地接入端点为 http://127.0.0.1:33080/v1 。客户在控制台创建、禁用和删除自己的 Key。模拟渠道使用 gpt-4o-mini 作为测试夹具模型名，返回固定文本。新建渠道后需等待网关刷新路由缓存。

## DeepSeek 联调

Windows 上的 probe-deepseek.ps1 从当前用户的 DPAPI 文件读取测试凭据，通过标准输入放入容器 tmpfs，结束时清除。渠道表保存 secret-ref:deepseek-pilot 引用。允许模型为 deepseek-v4-pro、deepseek-v4-flash，目标为官方 HTTPS Chat Completions。每次手动运行会调用付费接口，检查非流式、SSE、Usage、工具调用、多轮和 JSON。模拟验收命令不调用此脚本。该环境默认关闭自动重试与公开注册。

## 数据与验收

通过 docker compose -f deploy/local/compose.yaml stop 停止服务，命名卷保留数据。check-restore.ps1 在同一数据库容器创建临时恢复库，校验记录后删除临时库。生产异地恢复需独立验收。

本地依赖检查可运行 python deploy/local/scan_dependencies.py report.json，结果包含版本与 OSV 命中。上线前仍需完成供应账单核对、可达漏洞处置、硬预付持久账本及跨渠道故障演练。当前环境仅用于研发联调。

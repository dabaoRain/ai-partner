# 服务器部署问答与要点整理（新手向）

本文汇总部署过程中常见问题的说明。完整一步步操作请看 [deploy.md](deploy.md)。

目标：访问 `https://你的域名/home`，效果等同本地 `http://localhost:5173/home`。

---

## 1. 是否要把文档里所有命令都执行一遍？

不完全是「每一条都机械照抄」，而是：

- **仓库里已准备好的**（一般不用你再写）：`back/requirements.txt`、`deploy/nginx-ai-partner.conf`、`deploy/ai-partner-api.service`、`front/.env.production`
- **必须你自己在本机 + 阿里云上做的**：安全组 → 构建前端 → 上传 → 装软件/配 Key → systemd → Nginx → HTTPS → 验证

可以灵活替换的方式：

- 上传可用 `rsync` / `scp` / 宝塔面板，效果一样
- 前端可在本机构建只传 `dist`，服务器就不必装 Node
- 系统若不是 Ubuntu，`apt` 要换成对应包管理命令

核心是把这条链路跑通：**安全组 → 上传 → 后端服务 → Nginx → HTTPS → 验证**。

---

## 2. 「上传代码 + dist」是什么意思？

把家里电脑上的项目，拷贝到阿里云那台远程电脑上。

| 东西 | 通俗理解 | 放到服务器哪里 |
|------|----------|----------------|
| 项目源码 | 后端 Python、配置模板等 | `/opt/ai-partner/` |
| 前端打包结果 `dist` | 给浏览器看的成品网页 | `/var/www/ai-partner/dist/` |

类比：源码像菜谱和厨具，`dist` 像已经做好可端上桌的菜。Nginx 负责端菜（`dist`），后端用源码里的 Python 服务。

### 重要：在哪执行上传？

- **建目录** `mkdir`：可以在已登录的服务器里执行
- **真正上传** `rsync` / `scp`：必须在你**自己的 Mac**（有项目文件的那台电脑）上执行，不能在服务器里往自己传

若已登录服务器，只需：

```bash
mkdir -p /opt/ai-partner /var/www/ai-partner/dist
```

不必再写成 `ssh root@IP "mkdir ..."`（那种是「人还在自己电脑上」时用的）。

### 如何验证目录已创建？

在服务器执行：

```bash
ls -ld /opt/ai-partner /var/www/ai-partner/dist
```

成功会看到两行，开头有 `d` 表示目录。刚建好时目录是空的也正常。

---

## 3. 本机路径、服务器路径：命令要在哪执行？

- 命令里若是**绝对路径**（以 `/` 开头，如 `/opt/ai-partner/...`），在服务器**哪个目录**执行都可以
- 「根目录」是 `/`，root 用户登录后常在 `/root`（家目录），两者不是一回事
- 回到系统根目录：`cd /`
- 回用户家目录：`cd ~` 或 `cd /root`
- 看自己在哪：`pwd`

只有相对路径（如 `./xxx`）才必须先 `cd` 到对应目录。

---

## 4. 装 nginx / python / certbot，建 venv，配 API Key

| 要装/做的 | 通俗理解 |
|-----------|----------|
| nginx | 网站大门：域名访问时转发网页和接口 |
| python3 + venv | 给后端单独准备一个干净的 Python 小房间 |
| certbot | 申请免费 HTTPS 证书 |
| `.env` 里的 Key | 后端调用 DeepSeek 必需，否则无法聊天 |

前提：源码已在 `/opt/ai-partner`。

```bash
# 确认系统（Ubuntu/Debian 用 apt）
cat /etc/os-release

sudo apt update
sudo apt install -y nginx python3 python3-venv certbot python3-certbot-nginx

nginx -v
python3 --version
certbot --version

cd /opt/ai-partner/back
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
nano .env
# 改成：DEEPSEEK_API_KEY=你的真实Key
# 保存：Ctrl+O → Enter → Ctrl+X 退出

sudo mkdir -p /opt/ai-partner/back/sessions
sudo chown -R www-data:www-data /opt/ai-partner/back/sessions
sudo chown www-data:www-data /opt/ai-partner/back/.env
sudo chmod 600 /opt/ai-partner/back/.env
```

`.env` 注意：等号两边不要空格；一般不加引号；Key 不要发给别人。

临时手动测后端（测完 Ctrl+C）：

```bash
cd /opt/ai-partner/back
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
# 另开一个 SSH 窗口：
curl -s http://127.0.0.1:8000/health
# 期望：{"status":"ok","has_api_key":true}
```

---

## 5. 启用 systemd 跑后端

| 概念 | 通俗理解 |
|------|----------|
| systemd | 服务器管家，负责启停服务 |
| `.service` 文件 | 说明书：用谁、在哪、跑什么 |
| enable | 开机自启 |
| --now | 现在立刻启动 |

说明书位置：`/opt/ai-partner/deploy/ai-partner-api.service`  
内容要点：用 `www-data`，在 `/opt/ai-partner/back` 跑 uvicorn，只监听本机 `127.0.0.1:8000`。

```bash
# 若还在手动跑 uvicorn，先 Ctrl+C 停掉

sudo chown -R www-data:www-data /opt/ai-partner/back
sudo chmod 600 /opt/ai-partner/back/.env

sudo cp /opt/ai-partner/deploy/ai-partner-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-partner-api

sudo systemctl status ai-partner-api
# 看到 Active: active (running) 即成功；看完按 q 退出

curl -s http://127.0.0.1:8000/health
```

成功时常见输出包含：

- `Created symlink ... ai-partner-api.service`（已开机自启）
- `Active: active (running)`

常用命令：

```bash
sudo systemctl status ai-partner-api
sudo systemctl restart ai-partner-api
sudo systemctl stop ai-partner-api
sudo journalctl -u ai-partner-api -n 50 --no-pager
```

| 现象 | 可能原因 |
|------|----------|
| Permission denied | www-data 读不了目录或 .env |
| 找不到 uvicorn | .venv 没建好 |
| Address already in use | 8000 仍被手动进程占用 |
| has_api_key:false | .env 未配好或读不到 |

---

## 6. 装 Nginx 配置（替换 YOUR_DOMAIN）

作用：别人访问域名 → Nginx 提供 `/var/www/ai-partner/dist`，并把 `/api` 转到后端 8000。

域名写法：

- 对：`shbitrus.xyz` 或 `www.example.com`
- 错：`https://shbitrus.xyz`、`shbitrus.xyz/home`

```bash
ls /var/www/ai-partner/dist/index.html

# 把 shbitrus.xyz 换成你的域名
sudo sed 's/YOUR_DOMAIN/shbitrus.xyz/g' /opt/ai-partner/deploy/nginx-ai-partner.conf \
  | sudo tee /etc/nginx/sites-available/ai-partner

grep server_name /etc/nginx/sites-available/ai-partner

sudo ln -sf /etc/nginx/sites-available/ai-partner /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t && sudo systemctl reload nginx

curl -s http://127.0.0.1/api/health
# 浏览器可先试：http://你的域名/home
```

| 现象 | 可能原因 |
|------|----------|
| 浏览器打不开 | 安全组未放行 80；域名未解析到本机 |
| 出现 Nginx 默认欢迎页 | 默认站点未关掉或配置未启用 |
| 页面空白/404 | dist 未正确上传 |
| 页面能开但 /api 失败 | 后端服务未运行 |

---

## 7. Certbot 申请 HTTPS

```bash
sudo certbot --nginx -d shbitrus.xyz
```

交互说明：

1. **邮箱**：填真实能收信的邮箱，用于到期提醒。**不要输入 `c`**（`c` 是取消）
2. 若误按 `c` 出现 `An e-mail address or --register-unsafely-without-email must be provided`，重新执行上面命令即可
3. **同意服务条款**：输入 `Y`
4. **是否把邮箱分享给 EFF**：与证书无关，不想收宣传邮件就输入 `N`
5. 不想填邮箱可用（不推荐）：`sudo certbot --nginx -d 你的域名 --register-unsafely-without-email`

成功后浏览器打开：

- `https://你的域名/home`
- `https://你的域名/api/health`

确认安全组已放行 **443**。

---

## 8. 架构速览

```text
浏览器 --HTTPS--> Nginx
                   |-- 静态文件 --> /var/www/ai-partner/dist
                   |-- /api/* 去掉 /api 前缀 --> 127.0.0.1:8000 (uvicorn/FastAPI)
                                                    |
                                                    +--> DeepSeek API
                                                    +--> back/sessions 会话文件
```

- 前端请求仍用相对路径 `/api`（与本地 Vite 代理行为一致）
- 后端不对外暴露 8000，只给本机 Nginx 访问
- 语音识别（Web Speech API）在非 localhost 下需要 HTTPS

---

## 9. 日常更新

- **更新前端**：本机 `cd front && pnpm build`，再 `rsync front/dist/` 到服务器 `/var/www/ai-partner/dist/`
- **更新后端**：本机 `rsync` 源码到 `/opt/ai-partner/`，服务器执行 `sudo systemctl restart ai-partner-api`

---

## 10. 仓库里的部署相关文件

| 文件 | 作用 |
|------|------|
| `back/requirements.txt` | 后端 Python 依赖 |
| `deploy/nginx-ai-partner.conf` | Nginx 站点模板（含 SPA + `/api` + SSE） |
| `deploy/ai-partner-api.service` | systemd 单元模板 |
| `front/.env.production` | 生产环境同域 `/api` |
| `deploy.md` | 从零到上线的完整详细流程 |
| `server.md` | 本文：问答与要点整理 |

# 从零把本地项目部署到阿里云（新手完整流程）

本文面向几乎没有服务器经验的新手，按顺序做即可。  
补充说明与常见问答见 [server.md](server.md)。

**最终目标**：浏览器打开 `https://你的域名/home`，效果和本地 `http://localhost:5173/home` 一样。

下文示例域名用 `shbitrus.xyz`，示例 IP 用 `47.xx.xx.xx`，请全部换成你自己的。

---

## 总体在做什么（先建立印象）

本地开发时：

- 前端：`pnpm dev` 跑在 `5173`
- 后端：跑在 `8000`
- Vite 把浏览器的 `/api` 请求转给后端

上线后：

- 前端打成静态文件 `dist`，由 Nginx 提供
- 后端用 systemd 在后台一直跑（本机 8000）
- Nginx 用你的域名对外提供服务，并把 `/api` 转给后端
- Certbot 给域名加上 HTTPS（小锁），语音识别也需要 HTTPS

```text
你的电脑浏览器
    |
    | 访问 https://shbitrus.xyz
    v
阿里云服务器上的 Nginx
    |-- /           --> 网页文件（/var/www/ai-partner/dist）
    |-- /api/...    --> 后端（127.0.0.1:8000）
```

---

## 开始前你需要准备

1. **一台阿里云 Linux 服务器**（建议 Ubuntu），能开机、有公网 IP  
2. **已备案域名**，并已解析到该服务器公网 IP（A 记录）  
3. **能 SSH 登录**（知道 IP、用户名，常见是 `root`，以及密码或密钥）  
4. **DeepSeek API Key**（后端聊天要用）  
5. **本机已安装** Node.js、pnpm（用于 `pnpm build`）  
6. 本机项目路径示例：

```text
/Users/shaohaibin/项目/AIAgent/Python/AI-Partner
```

---

## 步骤 0：阿里云安全组放行端口

在阿里云控制台：

1. 找到你的 ECS 实例  
2. 安全组 → 配置规则 → 入方向  
3. 放行：
   - **TCP 22**（SSH 登录，若已能登录可不管）
   - **TCP 80**（网站 HTTP）
   - **TCP 443**（网站 HTTPS）
4. **不要**对公网放行 8000、5173

---

## 步骤 1：确认能登录服务器

在你自己的 Mac「终端」执行（换成真实 IP）：

```bash
ssh root@47.xx.xx.xx
```

- 若问 `Are you sure you want to continue connecting?` → 输入 `yes` 回车  
- 再输入密码（输入时可能不显示字符，正常）回车  

成功后提示符类似 `root@iZxxxxx:~#`。

先退出，回到自己电脑：

```bash
exit
```

连不上就先解决 SSH / 安全组 22，再继续后面步骤。

---

## 步骤 2：本机打包前端（生成 dist）

部署用的是**构建产物**，不是 `pnpm dev`。

在你的 Mac 终端：

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner/front
pnpm i
pnpm build
```

成功后应存在目录：`front/dist`（内含 `index.html` 等）。

---

## 步骤 3：在服务器上创建目录

### 方式 A：已登录服务器时

```bash
mkdir -p /opt/ai-partner /var/www/ai-partner/dist
ls -ld /opt/ai-partner /var/www/ai-partner/dist
```

看到两行目录信息即成功。然后：

```bash
exit
```

回到自己的 Mac。

### 方式 B：人还在自己电脑上时

```bash
ssh root@47.xx.xx.xx "mkdir -p /opt/ai-partner /var/www/ai-partner/dist"
```

| 目录 | 用途 |
|------|------|
| `/opt/ai-partner` | 放项目源码 |
| `/var/www/ai-partner/dist` | 放前端成品网页 |

---

## 步骤 4：从本机上传代码和 dist

**必须在自己的 Mac、项目根目录执行**（不要在服务器里执行 rsync 上传）。

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner

# ① 上传源码（排除大目录）
rsync -avz \
  --exclude 'front/node_modules' \
  --exclude 'front/dist' \
  --exclude 'back/.venv' \
  --exclude 'back/sessions' \
  --exclude '.git' \
  ./ root@47.xx.xx.xx:/opt/ai-partner/

# ② 上传前端成品到 Nginx 目录
rsync -avz front/dist/ root@47.xx.xx.xx:/var/www/ai-partner/dist/
```

`--exclude` 含义：这些大文件夹别传。`front/dist/` 末尾的 `/` 表示传「里面的内容」。

### 上传后如何检查？

```bash
ssh root@47.xx.xx.xx
ls /opt/ai-partner
ls /var/www/ai-partner/dist
```

期望：

- `/opt/ai-partner` 有 `back`、`front`、`deploy`、`server.md`、`deploy.md` 等  
- `/var/www/ai-partner/dist` 有 `index.html`

检查完可先留在服务器继续下一步，或 `exit` 后再 `ssh` 进来。

---

## 步骤 5：安装 nginx / python / certbot

以下默认系统为 **Ubuntu/Debian**（有 `apt`）。先确认：

```bash
cat /etc/os-release
```

然后：

```bash
sudo apt update
sudo apt install -y nginx python3 python3-venv certbot python3-certbot-nginx

nginx -v
python3 --version
certbot --version
```

能显示版本号即可。

---

## 步骤 6：创建 Python 虚拟环境并安装依赖

```bash
cd /opt/ai-partner/back
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`.venv` 就是后端专用的「Python 小房间」。

---

## 步骤 7：配置 DeepSeek API Key

```bash
cd /opt/ai-partner/back
cp .env.example .env
nano .env
```

改成类似：

```text
DEEPSEEK_API_KEY=sk-你的真实密钥
```

注意：等号两边不要空格；一般不加引号。

保存退出 nano：

1. `Ctrl + O`  
2. `Enter`  
3. `Ctrl + X`

确认：

```bash
cat /opt/ai-partner/back/.env
```

会话目录与权限：

```bash
sudo mkdir -p /opt/ai-partner/back/sessions
sudo chown -R www-data:www-data /opt/ai-partner/back/sessions
sudo chown www-data:www-data /opt/ai-partner/back/.env
sudo chmod 600 /opt/ai-partner/back/.env
```

（可选）手动测一下后端，测完用 `Ctrl+C` 停掉：

```bash
cd /opt/ai-partner/back
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

另开一个 SSH 窗口：

```bash
curl -s http://127.0.0.1:8000/health
```

期望：`{"status":"ok","has_api_key":true}`。

---

## 步骤 8：用 systemd 让后端后台常驻

这些命令里的路径都是绝对路径，**不必**先 `cd /`，在哪执行都行。

若刚才还在手动跑 uvicorn，先 `Ctrl+C` 停掉。

```bash
sudo chown -R www-data:www-data /opt/ai-partner/back
sudo chmod 600 /opt/ai-partner/back/.env

sudo cp /opt/ai-partner/deploy/ai-partner-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-partner-api

sudo systemctl status ai-partner-api
```

成功标志：

- `Active: active (running)`
- 可能看到 `Created symlink ...`（开机自启）

状态页看完按 **`q`** 退出，再执行：

```bash
curl -s http://127.0.0.1:8000/health
```

失败时看日志：

```bash
sudo journalctl -u ai-partner-api -n 50 --no-pager
```

常用：

```bash
sudo systemctl restart ai-partner-api
sudo systemctl stop ai-partner-api
```

此时后端只在服务器内部 `127.0.0.1:8000`，外网还不能直接用域名访问，需要 Nginx。

---

## 步骤 9：配置 Nginx（HTTP）

把下面的 `shbitrus.xyz` 换成你的真实域名（不要带 `http://`）：

```bash
ls /var/www/ai-partner/dist/index.html

sudo sed 's/YOUR_DOMAIN/shbitrus.xyz/g' /opt/ai-partner/deploy/nginx-ai-partner.conf \
  | sudo tee /etc/nginx/sites-available/ai-partner

grep server_name /etc/nginx/sites-available/ai-partner

sudo ln -sf /etc/nginx/sites-available/ai-partner /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t && sudo systemctl reload nginx
```

`nginx -t` 应显示 `syntax is ok` / `test is successful`。

本机验证：

```bash
curl -s http://127.0.0.1/api/health
```

自己电脑浏览器先试：

```text
http://shbitrus.xyz/home
```

能打开页面，说明 Nginx HTTP 已通（还没有小锁，正常）。

---

## 步骤 10：用 Certbot 申请 HTTPS

```bash
sudo certbot --nginx -d shbitrus.xyz
```

按提示操作：

| 提示 | 你怎么选 |
|------|----------|
| Enter email address | 填真实邮箱，回车。**不要输入 `c`**（那是取消） |
| 同意 Terms of Service | 输入 `Y` |
| 是否把邮箱分享给 EFF | 与证书无关，不想收邮件就输入 `N` |

若误按 `c` 取消，会提示必须提供邮箱。重新执行上面的 `certbot` 命令即可。

不想填邮箱（不推荐）：

```bash
sudo certbot --nginx -d shbitrus.xyz --register-unsafely-without-email
```

成功后一般会出现 Congratulations，并自动改 Nginx 为 HTTPS。

---

## 步骤 11：最终验证

在自己电脑浏览器打开：

1. `https://shbitrus.xyz/home` — 页面正常  
2. `https://shbitrus.xyz/api/health` — 返回类似 `{"status":"ok","has_api_key":true}`  
3. 发一条聊天 — 确认流式回复正常  
4. （可选）试语音输入 — 需要 HTTPS  

全部 OK，即部署完成。

---

## 日常如何更新

### 更新前端页面

在自己 Mac：

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner/front
pnpm build

cd ..
rsync -avz front/dist/ root@47.xx.xx.xx:/var/www/ai-partner/dist/
```

一般不用重启 Nginx。

### 更新后端代码

在自己 Mac：

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner
rsync -avz \
  --exclude 'front/node_modules' \
  --exclude 'front/dist' \
  --exclude 'back/.venv' \
  --exclude 'back/sessions' \
  --exclude '.git' \
  ./ root@47.xx.xx.xx:/opt/ai-partner/
```

在服务器：

```bash
sudo systemctl restart ai-partner-api
sudo systemctl status ai-partner-api
```

若改了 `requirements.txt`，还要在服务器：

```bash
cd /opt/ai-partner/back
.venv/bin/pip install -r requirements.txt
sudo systemctl restart ai-partner-api
```

---

## 出问题时怎么查

```bash
# 后端是否在跑
sudo systemctl status ai-partner-api
curl -s http://127.0.0.1:8000/health

# 后端日志
sudo journalctl -u ai-partner-api -n 50 --no-pager

# Nginx 是否在跑、配置是否正确
sudo systemctl status nginx
sudo nginx -t

# 前端文件在不在
ls /var/www/ai-partner/dist/index.html
```

| 现象 | 优先检查 |
|------|----------|
| SSH 连不上 | 安全组 22、IP、密码/密钥 |
| 域名打不开 | 解析是否指向本机；安全组 80/443 |
| 只有默认欢迎页 | 是否启用了 ai-partner 站点、是否关掉 default |
| 页面空白 | dist 是否上传完整 |
| 页面有、接口挂 | ai-partner-api 是否 running；`/api/health` |
| 证书申请失败 | 域名解析、80 是否通、邮箱是否误按 c 取消 |

---

## 清单（可打勾）

- [ ] 安全组放行 22 / 80 / 443  
- [ ] 本机 `pnpm build` 成功  
- [ ] 服务器目录 `/opt/ai-partner`、`/var/www/ai-partner/dist` 已创建  
- [ ] 源码与 dist 已上传并 `ls` 检查通过  
- [ ] 已安装 nginx、python3-venv、certbot  
- [ ] 已建 `.venv` 并 `pip install -r requirements.txt`  
- [ ] 已配置 `back/.env` 中 `DEEPSEEK_API_KEY`  
- [ ] `systemctl status ai-partner-api` 为 `active (running)`  
- [ ] `curl http://127.0.0.1:8000/health` 正常  
- [ ] Nginx 配置已替换域名并 `nginx -t` 通过  
- [ ] HTTP 下 `/home` 与 `/api/health` 可访问  
- [ ] certbot 申请 HTTPS 成功  
- [ ] `https://域名/home` 与聊天功能正常  

更细的概念解释见 [server.md](server.md)。

# 前端改动同步到服务器

适用于：**服务器已按 [deploy.md](deploy.md) 部署完成**，本次只更新前端（例如移动端布局），不改后端。

原理：Nginx 读的是成品目录 `/var/www/ai-partner/dist`，不是 `front` 源码。所以要在本机重新 `pnpm build`，再把新的 `dist` 覆盖上去。

```text
本机 front 改动
    → pnpm build 生成 front/dist
    → rsync 覆盖到服务器 /var/www/ai-partner/dist
    → 浏览器打开 https://你的域名/home 验证
```

下文示例 IP `47.xx.xx.xx`、域名 `shbitrus.xyz`，请换成你自己的。  
项目根目录示例：`/Users/shaohaibin/项目/AIAgent/Python/AI-Partner`

---

## 开始前确认

1. 本机已能 SSH：`ssh root@47.xx.xx.xx`
2. 服务器上已有目录：`/var/www/ai-partner/dist`（且里面有旧版 `index.html`）
3. 本机已装 Node / pnpm，能进入 `front` 目录构建
4. 生产环境用 [`front/.env.production`](../front/.env.production)（同域 `/api`），一般不用改

---

## 步骤 1：本机构建前端

在自己的 **Mac 终端**执行（不要在服务器上）：

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner/front

# 依赖有变或久未安装时再跑；日常小改可跳过
pnpm i

pnpm build
```

成功标志：出现 `front/dist`，且含 `index.html`。

快速检查：

```bash
ls dist/index.html
ls dist/assets | head
```

---

## 步骤 2：上传 dist 到 Nginx 目录

**路径必须对应当前目录**，否则会传 0 个文件（页面永远是旧的）。

### 方式 A：人在项目根目录（推荐）

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner

# 先确认本地产物存在（应能列出 index.html）
ls front/dist/index.html

rsync -avz --delete front/dist/ root@47.xx.xx.xx:/var/www/ai-partner/dist/
```

### 方式 B：人已经在 front 目录里

构建刚做完、终端还在 `.../AI-Partner/front` 时，路径要用 `dist/`，**不要再写 `front/dist/`**：

```bash
# 当前目录应是 front，pwd 末尾是 /front
pwd
ls dist/index.html

rsync -avz --delete dist/ root@47.xx.xx.xx:/var/www/ai-partner/dist/
```

说明：

| 参数 | 作用 |
|------|------|
| `-avz` | 归档、可读输出、压缩传输 |
| `--delete` | 删掉服务器上本地已不存在的旧资源（避免旧 hash 文件残留） |
| 末尾 `/` | 传「目录里的内容」，不是再套一层文件夹 |

上传成功时终端应出现多行文件列表（`index.html`、`assets/...`、`js/...`），且 **Transfer starting** 后面数字 **> 0**。若看到 `No such file or directory` / `Transfer starting: 0 files`，说明本地路径写错了，服务器上的 dist **完全没更新**。

一般**不用**重启 Nginx。

确认服务器上已是新文件：

```bash
ssh root@47.xx.xx.xx "ls -la /var/www/ai-partner/dist && ls /var/www/ai-partner/dist/assets | head"
```

期望能看到带新 hash 的 css/js（例如含 `HomeView-....css`）。
---

## 步骤 3（建议）：顺带同步前端源码到 /opt

可选。方便服务器上留一份与线上一致的源码，**不影响**用户看到的页面（页面只看 `/var/www/.../dist`）。

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner

rsync -avz \
  --exclude 'node_modules' \
  --exclude 'dist' \
  front/ root@47.xx.xx.xx:/opt/ai-partner/front/
```

---

## 步骤 4：浏览器验证

1. 打开 `https://shbitrus.xyz/home`（换成你的域名）
2. 若样式像旧版：强制刷新（Mac Chrome：`Cmd+Shift+R`），或无痕窗口再开
3. 手机或 DevTools 切到约 375 宽：
   - 默认全宽聊天区
   - 左上角菜单可打开侧栏
   - 点遮罩 / 选会话后侧栏关闭
4. 桌面宽屏：侧栏常驻，与之前一致
5. 发一条消息，确认 `/api` 与流式回复仍正常

健康检查（可选）：

```bash
curl -s https://shbitrus.xyz/api/health
# 期望类似：{"status":"ok","has_api_key":true}
```

---

## 一键命令（复制用）

把 IP 换成真实值后，在 Mac 上从项目根目录执行：

```bash
cd /Users/shaohaibin/项目/AIAgent/Python/AI-Partner/front \
  && pnpm build \
  && cd .. \
  && rsync -avz --delete front/dist/ root@47.xx.xx.xx:/var/www/ai-partner/dist/
```

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `pnpm build` 失败 | 先 `pnpm i`；本机 Node 建议 18+ |
| rsync 连不上 | 检查 SSH、安全组 22、IP |
| rsync 报 `No such file` / `0 files` | 当前目录与路径不匹配：在 `front` 里应传 `dist/`；在项目根应传 `front/dist/` |
| 页面还是旧的 | 先看上次 rsync 是否真传成功；再硬刷新 / 无痕窗口 |
| 页面空白 | `ls` 看 `index.html` 是否在；Nginx `root` 是否指向该目录 |
| 接口挂了 | 本次只更前端不应影响后端；查 `systemctl status ai-partner-api` |

本次**只更新前端**时：

- 不需要 `systemctl restart ai-partner-api`
- 不需要重新跑 certbot
- 不需要改 Nginx 配置（除非你改了部署路径）

若以后还要更新后端，见 [deploy.md 日常如何更新](deploy.md#日常如何更新) 或 [server.md §9](server.md#9-日常更新)。

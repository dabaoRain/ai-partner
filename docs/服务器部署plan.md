阿里云 Nginx + HTTPS 域名部署

目标架构

访问 https://你的域名/home，效果等同本地 http://localhost:5173/home。

flowchart LR
User["浏览器"] -->|"https://域名"| Nginx
Nginx -->|"静态 dist"| Front["front/dist"]
Nginx -->|"/api 去掉前缀"| Uvicorn["127.0.0.1:8000"]
Uvicorn --> FastAPI
FastAPI --> Sessions["back/sessions"]
FastAPI --> DeepSeek

前端：构建后的 SPA，由 Nginx 提供；/ 重定向到 /home（已有路由逻辑）

后端：uvicorn 只监听本机 127.0.0.1:8000，不对外暴露

API：浏览器仍请求相对路径 /api/...（与现有 [front/src/utils/request.js](front/src/utils/request.js) 一致）；Nginx 去掉 /api 前缀转发到后端（复刻 Vite 开发代理）

HTTPS：Certbot + Let’s Encrypt；语音识别（Web Speech API）在非 localhost 下必须 HTTPS

仓库内需补充的产物

在项目里新增部署文件（执行阶段落地），便于拷到服务器：

文件

作用

[back/requirements.txt](back/requirements.txt)

当前缺失，补上 fastapi、uvicorn、openai、python-dotenv

deploy/nginx-ai-partner.conf

Nginx 站点配置（静态 + /api 反代 + SSE）

deploy/ai-partner-api.service

systemd 单元，生产启动后端

修正 [front/.env.production](front/.env.production)

VITE_API_BASE_URL 改为同域占位（如空或同域名）；实际请求只用 VITE_API_PREFIX=/api，保持相对路径即可

后端启动方式：生产用 systemd 调 uvicorn，不要再用 python main.py（其内 reload=True 且仅适合本机开发）。

Nginx 关键配置要点

server {
listen 80;
server_name 你的域名; # Certbot 会改成 443 + 证书

    root /var/www/ai-partner/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;  # Vue history 模式
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;  # 注意末尾 /，去掉 /api 前缀
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection '';
        proxy_buffering off;                 # SSE 流式聊天必需
        proxy_cache off;
        proxy_read_timeout 3600s;
    }

}

服务器操作步骤（你执行 / 按文档操作）

阿里云安全组：放行 80、443；不必放行 8000、5173

安装依赖：nginx、python3+venv、nodejs/pnpm（或本机构建后只上传 dist）、certbot + python3-certbot-nginx

目录建议：

代码：/opt/ai-partner（含 front、back）

前端产物：/var/www/ai-partner/dist（或 Nginx root 指向 front/dist）

后端：

cd back && python3 -m venv .venv && pip install -r requirements.txt

配置 back/.env 中 DEEPSEEK_API_KEY

安装并启用 ai-partner-api.service（WorkingDirectory=back，uvicorn main:app --host 127.0.0.1 --port 8000）

前端：本机或服务器执行 cd front && pnpm i && pnpm build，把 dist 放到 Nginx root

Nginx：放入站点 conf → nginx -t → reload

HTTPS：sudo certbot --nginx -d 你的域名（自动改 conf 并续期）

验证：

https://域名/home 页面正常

https://域名/api/health（或现有 health 路径）返回正常

发一条聊天确认 SSE 流式正常

代码侧小改（可选但建议）

[back/main.py](back/main.py) 保留开发入口即可；生产不依赖它

不改前端 API 调用方式；同域 /api 最简单，避免 CORS 与跨域 Cookie 问题

不在本次范围

Docker

把 API 拆到独立子域名

自动 CI/CD（可后续加）

你需要准备的信息

执行/写配置时把 Nginx 里的 server_name 换成真实域名；若你提供域名字符串，配置文件可直接写成最终值。

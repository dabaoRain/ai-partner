请帮我初始化一个基于 Vue 3 + Vite 的企业级前端项目，UI 框架使用 Element Plus，不使用 TypeScript。

技术栈要求：

- Vue 3（Composition API）
- Vite 5
- Element Plus
- Vue Router 4
- Pinia（状态管理）
- JavaScript（ES Module，不使用 TS）
- SCSS

项目规范：

- 使用 pnpm 管理依赖
- ESLint + Prettier 代码规范（使用 JavaScript 配置）
- 按需引入 Element Plus（使用 unplugin-vue-components 和 unplugin-auto-import）

目录结构：
├── src/
│ ├── api/ # API 接口
│ ├── assets/ # 静态资源
│ ├── components/ # 公共组件
│ ├── composables/ # 组合式函数
│ ├── layouts/ # 布局组件
│ ├── router/ # 路由配置
│ ├── store/ # Pinia 状态
│ ├── styles/ # 全局样式
│ ├── utils/ # 工具函数
│ └── views/ # 页面组件

配置文件：

- vite.config.js（非 .ts）
- .eslintrc.js（非 .ts）
- 配置路径别名 @ 指向 src
- 配置代理解决跨域问题
- 配置环境变量
- 配置打包优化

请生成完整的项目代码和配置文件，所有文件使用 .js 后缀。

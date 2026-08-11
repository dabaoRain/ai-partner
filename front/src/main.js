import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import '@/styles/index.scss'
// 命令式 API 不会走按需样式注入，需手动引入
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.mount('#app')

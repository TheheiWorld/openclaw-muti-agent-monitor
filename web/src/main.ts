import { createApp } from 'vue'
import { ElLoading } from 'element-plus'
import 'element-plus/es/components/loading/style/css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(ElLoading)
app.use(router)

app.mount('#app')

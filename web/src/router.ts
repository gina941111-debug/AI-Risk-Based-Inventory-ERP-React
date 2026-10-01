import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import WorkspaceView from './views/WorkspaceView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: '/login', component: LoginView }, { path: '/', component: WorkspaceView }],
})

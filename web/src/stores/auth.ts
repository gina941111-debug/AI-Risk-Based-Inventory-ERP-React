import { defineStore } from 'pinia'
import { api, errorMessage } from '../api'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null as User | null, loading: false, error: '' }),
  getters: { isAuthenticated: (state) => Boolean(state.user) },
  actions: {
    async restore() { try { const { data } = await api.get('/auth/me'); this.user = data } catch { this.user = null } },
    async login(username: string, password: string) { this.loading = true; this.error = ''; try { const { data } = await api.post('/auth/login', { username, password }); this.user = data; return true } catch (e) { this.error = errorMessage(e); return false } finally { this.loading = false } },
    async logout() { await api.post('/auth/logout').catch(() => undefined); this.user = null },
  },
})

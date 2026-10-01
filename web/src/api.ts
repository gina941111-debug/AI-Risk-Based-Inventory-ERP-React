import axios from 'axios'

export const api = axios.create({ baseURL: '/api/v1', withCredentials: true })
export const errorMessage = (error: any) => error?.response?.data?.detail || error?.message || '請求失敗'

import axios from 'axios'

export const api = axios.create({ baseURL: '/api/v1', withCredentials: true })
export function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || error.message
  return error instanceof Error ? error.message : '請求失敗'
}

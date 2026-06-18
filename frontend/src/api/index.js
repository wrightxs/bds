import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

/** 获取仪表盘摘要 */
export function getDashboard(date) {
  return api.get('/dashboard', { params: date ? { date } : {} })
}

/** 获取成交额前100 */
export function getTop100(date) {
  return api.get('/top100', { params: date ? { date } : {} })
}

/** 获取涨停股票列表 */
export function getLimitUp(date, board) {
  return api.get('/limit_up', { params: { ...(date && { date }), ...(board && { board }) } })
}

/** 获取可用日期列表 */
export function getDates() {
  return api.get('/dates')
}

export default api

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

/** 手动触发数据抓取，force=true 强制清除已有数据并重新抓取 */
export function triggerFetch(date, force = false) {
  const params = {}
  if (date) params.date = date
  if (force) params.force = true
  return api.post('/fetch', null, { params })
}

/** 获取均线突破分析 */
export function getRightTrade(days, date) {
  return api.get('/right_trade', { params: { days, ...(date && { date }) } })
}

/** 获取缠论买卖点 */
export function getChanTheory(date) {
  return api.get('/chan_theory', { params: date ? { date } : {} })
}

/** 获取当前数据源 */
export function getDataSource() {
  return api.get('/data-source')
}

/** 切换数据源 */
export function setDataSource(source) {
  return api.post('/data-source', null, { params: { source } })
}

/** 获取单只股票K线数据 */
export function getKline(stockCode, days = 60) {
  return api.get('/kline', { params: { stock_code: stockCode, days } })
}

export default api

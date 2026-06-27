/** 判断今天是否为工作日（周一至周五） */
export function isTodayWeekday() {
  const day = new Date().getDay()
  return day >= 1 && day <= 5
}

/** 返回今天日期字符串 YYYY-MM-DD */
export function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

/** 当天只请求一次的缓存：返回 true 表示今天已请求过 */
let _lastFetchDay = ''
export function wasFetchedToday() {
  return _lastFetchDay === todayStr()
}
export function markFetchedToday() {
  _lastFetchDay = todayStr()
}

/**
 * 判断是否应显示"查询中"提示
 * @param {string|null} displayedDate - 当前展示数据的日期
 * @param {string} userSelectedDate - 用户选择的日期（空字符串表示未选择）
 * @returns {boolean}
 */
export function isQueryingToday(displayedDate, userSelectedDate) {
  if (!isTodayWeekday()) return false
  const today = todayStr()
  // 用户明确选择了历史日期，不提示
  if (userSelectedDate && userSelectedDate !== today) return false
  // 展示的数据日期不是今天，说明当天数据未生成
  if (displayedDate !== today) return true
  return false
}

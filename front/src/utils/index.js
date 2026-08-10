/**
 * 格式化日期时间
 * @param {Date|string|number} value
 * @param {string} pattern
 */
export function formatDate(value, pattern = 'YYYY-MM-DD HH:mm:ss') {
  if (!value) return ''
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const map = {
    YYYY: String(date.getFullYear()),
    MM: String(date.getMonth() + 1).padStart(2, '0'),
    DD: String(date.getDate()).padStart(2, '0'),
    HH: String(date.getHours()).padStart(2, '0'),
    mm: String(date.getMinutes()).padStart(2, '0'),
    ss: String(date.getSeconds()).padStart(2, '0'),
  }

  return pattern.replace(/YYYY|MM|DD|HH|mm|ss/g, (key) => map[key])
}

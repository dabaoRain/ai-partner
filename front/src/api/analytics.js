import request from '@/utils/request'

export function postEventsBatch(events) {
  return request({
    url: '/events/batch',
    method: 'post',
    data: { events },
  })
}

export function postFeedback(data) {
  return request({
    url: '/feedback',
    method: 'post',
    data,
  })
}

export function fetchAnalyticsSummary(days = 7) {
  return request({
    url: '/analytics/summary',
    method: 'get',
    params: { days },
  })
}

/**
 * 客户端埋点（失败静默）
 * @param {string} eventName
 * @param {{ session_id?: string, props?: object }} [options]
 */
export async function trackClientEvent(eventName, options = {}) {
  try {
    await postEventsBatch([
      {
        event_name: eventName,
        session_id: options.session_id || '',
        props: options.props || {},
      },
    ])
  } catch (error) {
    console.error(error)
  }
}

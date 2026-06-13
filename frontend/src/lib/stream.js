export function parseSseDataLine(line) {
  if (!line.startsWith('data:')) return null
  const raw = line.slice(5).trim()
  if (!raw) return null
  return JSON.parse(raw)
}

export function beginUserTurn(messages, state, content) {
  const userMessage = {
    role: 'user',
    content,
    toolEvents: [],
    toolsOpen: false,
  }
  messages.push(userMessage)
  state.assistantDraft = ''
  state.runStatus = '正在连接 Agent...'
  state.toolEvents = userMessage.toolEvents
  return userMessage
}

export function appendStreamEvent(state, event) {
  if (!event) return
  if (event.type === 'token') {
    state.assistantDraft += event.content || ''
    state.runStatus = ''
    return
  }
  if (event.type === 'status') {
    state.runStatus = event.message || ''
    return
  }
  if (event.type === 'tool_args') {
    upsertToolEvent(state.toolEvents, normalizeToolEvent(event))
    state.runStatus = `正在准备 ${event.display_name || event.tool_name || '工具'} 参数...`
    return
  }
  if (event.type === 'tool_start' || event.type === 'tool_result') {
    upsertToolEvent(state.toolEvents, normalizeToolEvent(event))
    if (event.type === 'tool_start') {
      state.runStatus = `正在调用 ${event.display_name || event.tool_name || '工具'}...`
    }
    if (event.type === 'tool_result') {
      state.runStatus = '工具返回，正在整理回答...'
    }
  }
}

export function commitFinalAnswer(messages, state, event) {
  const content = event?.content || state.assistantDraft
  if (content) {
    messages.push({ role: 'assistant', content })
  }
  state.assistantDraft = ''
  state.runStatus = ''
}

export function normalizeErrorMessage(message) {
  if (!message) return '请求失败，请稍后重试。'
  if (message.includes('ENGINE_RESPONSE_DATA_ERROR')) {
    return (
      '模型返回数据格式异常（ENGINE_RESPONSE_DATA_ERROR）。通常是模型在工具调用阶段返回了不符合接口要求的数据；' +
      '请重试，或减少一次请求中的工具/约束复杂度。'
    )
  }
  return message
}

function normalizeToolEvent(event) {
  if (event.type === 'tool_args') {
    return {
      ...event,
      status: event.status || 'running',
    }
  }
  return {
    ...event,
    status: event.status || (event.type === 'tool_result' ? 'done' : 'running'),
  }
}

function upsertToolEvent(toolEvents, event) {
  const key = toolEventKey(event)
  const index = toolEvents.findIndex((item) => {
    return toolEventKey(item) === key
  })
  if (index >= 0) {
    const existing = toolEvents[index]
    const { args_delta: _argsDelta, ...eventWithoutDelta } = event
    toolEvents[index] = {
      ...existing,
      ...eventWithoutDelta,
      args:
        event.type === 'tool_args'
          ? `${existing.args || ''}${event.args_delta || ''}`
          : event.args !== undefined
            ? event.args
            : existing.args,
    }
    return
  }
  const { args_delta: _argsDelta, ...eventWithoutDelta } = event
  toolEvents.push({
    ...eventWithoutDelta,
    args: event.type === 'tool_args' ? event.args_delta || '' : event.args,
  })
}

function toolEventKey(event) {
  return event.tool_call_id || event.call_id || event.tool_name || event.display_name || event.type
}

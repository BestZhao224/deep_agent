import { describe, expect, it } from 'vitest'

import {
  appendStreamEvent,
  beginUserTurn,
  commitFinalAnswer,
  normalizeErrorMessage,
  parseSseDataLine,
} from '../src/lib/stream'

describe('stream helpers', () => {
  it('parses an SSE data line into an event object', () => {
    const event = parseSseDataLine('data: {"type":"token","content":"你好"}')

    expect(event).toEqual({ type: 'token', content: '你好' })
  })

  it('keeps one compact tool event per tool instead of appending noisy chunks', () => {
    const state = { assistantDraft: '', toolEvents: [] }

    appendStreamEvent(state, { type: 'token', content: '东京' })
    appendStreamEvent(state, { type: 'tool_start', tool_name: 'search_web' })
    appendStreamEvent(state, { type: 'tool_result', tool_name: 'search_web', result: 'found' })

    expect(state.assistantDraft).toBe('东京')
    expect(state.toolEvents).toEqual([
      { type: 'tool_result', tool_name: 'search_web', status: 'done', result: 'found' },
    ])
  })

  it('attaches compact tool steps to the active user turn collapsed by default', () => {
    const state = { assistantDraft: '', toolEvents: [] }
    const messages = []

    beginUserTurn(messages, state, '帮我规划东京 5 天行程')
    appendStreamEvent(state, {
      type: 'tool_start',
      tool_call_id: 'call-search-1',
      tool_name: 'search_web',
      display_name: '联网搜索',
    })
    appendStreamEvent(state, {
      type: 'tool_result',
      tool_call_id: 'call-search-1',
      tool_name: 'search_web',
      display_name: '联网搜索',
      args: '{"query":"东京美食"}',
      result: '找到 3 条结果',
    })

    expect(messages).toEqual([
      {
        role: 'user',
        content: '帮我规划东京 5 天行程',
        toolEvents: [
          {
            type: 'tool_result',
            tool_call_id: 'call-search-1',
            tool_name: 'search_web',
            display_name: '联网搜索',
            status: 'done',
            args: '{"query":"东京美食"}',
            result: '找到 3 条结果',
          },
        ],
        toolsOpen: false,
      },
    ])
    expect(state.toolEvents).toBe(messages[0].toolEvents)
  })

  it('shows immediate and streamed run status while waiting for tokens or tools', () => {
    const state = { assistantDraft: '', toolEvents: [], runStatus: '' }
    const messages = []

    beginUserTurn(messages, state, '帮我规划东京旅行')
    expect(state.runStatus).toBe('正在连接 Agent...')

    appendStreamEvent(state, { type: 'status', message: '正在分析你的需求...' })
    expect(state.runStatus).toBe('正在分析你的需求...')

    appendStreamEvent(state, { type: 'tool_start', tool_name: 'search_web', display_name: '联网搜索' })
    expect(state.runStatus).toBe('正在调用 联网搜索...')
  })

  it('appends streamed tool args onto the matching tool step', () => {
    const state = { assistantDraft: '', toolEvents: [], runStatus: '' }
    const messages = []

    beginUserTurn(messages, state, '帮我规划东京旅行')
    appendStreamEvent(state, {
      type: 'tool_start',
      tool_call_id: 'call-todo',
      tool_name: 'write_todos',
      display_name: '规划任务',
    })
    appendStreamEvent(state, {
      type: 'tool_args',
      tool_call_id: 'call-todo',
      tool_name: 'write_todos',
      display_name: '规划任务',
      args_delta: '{"todos":',
    })
    appendStreamEvent(state, {
      type: 'tool_args',
      tool_call_id: 'call-todo',
      tool_name: 'write_todos',
      display_name: '规划任务',
      args_delta: '["查询天气"]}',
    })

    expect(state.toolEvents).toEqual([
      {
        type: 'tool_args',
        tool_call_id: 'call-todo',
        tool_name: 'write_todos',
        display_name: '规划任务',
        status: 'running',
        args: '{"todos":["查询天气"]}',
      },
    ])
  })

  it('commits final answer and clears streaming draft', () => {
    const state = { assistantDraft: '最终答案', toolEvents: [] }
    const messages = []

    commitFinalAnswer(messages, state, { content: '最终答案' })

    expect(messages).toEqual([{ role: 'assistant', content: '最终答案' }])
    expect(state.assistantDraft).toBe('')
  })

  it('explains raw engine response data errors from older backends', () => {
    expect(normalizeErrorMessage('API 调用失败：ENGINE_RESPONSE_DATA_ERROR')).toContain(
      '模型返回数据格式异常'
    )
  })
})

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'

import { fetchSession, fetchSessions, streamChat } from './api/chat'
import { beginUserTurn, commitFinalAnswer, normalizeErrorMessage } from './lib/stream'

const sessions = ref([])
const activeThreadId = ref(null)
const input = ref('')
const loading = ref(false)
const error = ref('')
const messages = ref([])
const streamState = reactive({ assistantDraft: '', toolEvents: [], runStatus: '' })
const messagesEnd = ref(null)

async function loadSessions() {
  sessions.value = await fetchSessions()
}

async function openSession(threadId) {
  activeThreadId.value = threadId
  const session = await fetchSession(threadId)
  messages.value = session.messages || []
  streamState.assistantDraft = ''
  streamState.toolEvents = []
  streamState.runStatus = ''
  await scrollToBottom()
}

async function scrollToBottom() {
  await nextTick()
  messagesEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
}

function resetCurrentChat() {
  activeThreadId.value = null
  messages.value = []
  streamState.assistantDraft = ''
  streamState.toolEvents = []
  streamState.runStatus = ''
  error.value = ''
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  error.value = ''
  loading.value = true
  input.value = ''
  beginUserTurn(messages.value, streamState, text)
  await scrollToBottom()

  try {
    await streamChat({
      message: text,
      threadId: activeThreadId.value,
      state: streamState,
      onEvent(event) {
        if (event.type === 'thread') {
          activeThreadId.value = event.thread_id
        }
        if (
          event.type === 'status' ||
          event.type === 'token' ||
          event.type === 'tool_start' ||
          event.type === 'tool_args' ||
          event.type === 'tool_result'
        ) {
          scrollToBottom()
        }
        if (event.type === 'done') {
          commitFinalAnswer(messages.value, streamState, event)
          scrollToBottom()
        }
        if (event.type === 'error') {
          error.value = normalizeErrorMessage(event.message)
          scrollToBottom()
        }
      },
    })
    await loadSessions()
  } catch (err) {
    error.value = normalizeErrorMessage(err.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadSessions)
</script>

<template>
  <main class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">P</span>
        <div>
          <strong>PersonalOps</strong>
          <small>DeepAgent Platform</small>
        </div>
      </div>
      <button class="new-chat" @click="resetCurrentChat">新会话</button>
      <nav class="sessions">
        <button
          v-for="session in sessions"
          :key="session.thread_id"
          :class="{ active: session.thread_id === activeThreadId }"
          @click="openSession(session.thread_id)"
        >
          {{ session.title || '新会话' }}
        </button>
      </nav>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <h1>旅行规划 Agent</h1>
          <p>DeepSeek + DeepAgents + 智谱搜索 / AMap MCP / 天气 / 汇率</p>
        </div>
        <span class="status">工具过程已聚合展示</span>
      </header>

      <section class="messages">
        <article v-if="messages.length === 0" class="empty">
          <h2>从一次真实旅行计划开始</h2>
          <p>例如：帮我规划一个 5 天东京旅行，预算 8000 人民币，偏美食和城市漫步。</p>
        </article>

        <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
          <span>{{ message.role === 'user' ? '你' : 'Agent' }}</span>
          <p>{{ message.content }}</p>
          <div v-if="message.role === 'user' && message.toolEvents?.length" class="turn-tools">
            <button class="turn-tools-toggle" @click="message.toolsOpen = !message.toolsOpen">
              <span>{{ message.toolsOpen ? '收起执行过程' : `展开执行过程（${message.toolEvents.length}）` }}</span>
              <span aria-hidden="true">{{ message.toolsOpen ? '−' : '+' }}</span>
            </button>
            <div v-if="message.toolsOpen" class="turn-tools-panel">
              <div
                v-for="event in message.toolEvents"
                :key="event.tool_call_id || event.call_id || event.tool_name || event.display_name"
                class="tool-event"
              >
                <div>
                  <strong>{{ event.display_name || event.tool_name || event.type }}</strong>
                  <small>{{ event.status === 'done' ? '已完成' : '运行中' }}</small>
                </div>
                <code>
                  <template v-if="event.args">参数：{{ event.args }}&#10;</template><template v-if="event.status === 'done'">结果：{{ event.result || '已完成' }}</template><template v-else>等待工具返回...</template>
                </code>
              </div>
            </div>
          </div>
        </article>

        <article v-if="loading && (streamState.assistantDraft || streamState.runStatus)" class="message assistant">
          <span>Agent</span>
          <p>{{ streamState.assistantDraft || streamState.runStatus }}</p>
        </article>

        <p v-if="error" class="error">{{ error }}</p>
        <div ref="messagesEnd" />
      </section>

      <form class="composer" @submit.prevent="sendMessage">
        <textarea
          v-model="input"
          :disabled="loading"
          rows="3"
          placeholder="输入你的旅行规划需求..."
        />
        <button :disabled="loading || !input.trim()">
          {{ loading ? '生成中' : '发送' }}
        </button>
      </form>
    </section>
  </main>
</template>

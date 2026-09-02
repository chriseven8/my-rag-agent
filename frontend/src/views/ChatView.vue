<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'

import { askStream } from '../api/client'
import type { Reference } from '../types'

interface Message {
  role: 'user' | 'assistant'
  text: string
  refs: Reference[]
  noEvidence: boolean
  streaming: boolean
}

const messages = ref<Message[]>([])
const input = ref('')
const busy = ref(false)
const listEl = ref<HTMLElement | null>(null)
let controller: AbortController | null = null

function pushMessage(role: Message['role']): Message {
  const m: Message = { role, text: '', refs: [], noEvidence: false, streaming: false }
  messages.value.push(m)
  return m
}

async function scrollBottom(): Promise<void> {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

async function send(): Promise<void> {
  const query = input.value.trim()
  if (!query || busy.value) return
  input.value = ''

  const bot = pushMessage('assistant')
  bot.streaming = true
  busy.value = true
  controller = new AbortController()
  await scrollBottom()

  try {
    await askStream(
      query,
      (text) => {
        bot.text += text
        void scrollBottom()
      },
      (done) => {
        bot.streaming = false
        bot.noEvidence = done.no_evidence
        bot.text = done.answer
        bot.refs = done.references
      },
      controller.signal,
    )
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      ElMessage.error(`请求出错:${(e as Error).message}`)
    }
  } finally {
    bot.streaming = false
    busy.value = false
    controller = null
    await scrollBottom()
  }
}

function stop(): void {
  controller?.abort()
}
</script>

<template>
  <div class="chat-view">
    <div ref="listEl" class="msg-list">
      <div v-for="(m, i) in messages" :key="i" class="row" :class="m.role">
        <div class="avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
        <div class="bubble">
          <div class="text">
            {{ m.text }}
            <span v-if="m.streaming" class="caret">▍</span>
          </div>
          <template v-if="m.role === 'assistant' && !m.streaming">
            <div v-if="m.noEvidence" class="no-evidence">本次未检索到足够证据,未生成基于文档的回答。</div>
            <div v-else-if="m.refs.length" class="refs">
              <div class="ref-title">引用来源</div>
              <el-card v-for="r in m.refs" :key="r.index" shadow="never" class="ref-card">
                <div class="ref-head">
                  <span class="ref-index">[{{ r.index }}]</span>
                  <span class="ref-doc">{{ r.doc_name }}</span>
                  <span class="ref-sec">{{ r.section_path || '全文' }}</span>
                </div>
                <div class="ref-snippet">{{ r.snippet }}</div>
              </el-card>
            </div>
          </template>
        </div>
      </div>
      <div v-if="!messages.length" class="empty">
        <el-empty description="先在「文档管理」上传文档,然后在这里提问试试" :image-size="90" />
      </div>
    </div>

    <div class="composer">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="输入问题,Enter 发送 / Shift+Enter 换行"
        :disabled="busy"
        @keydown.enter.exact.prevent="send"
      />
      <div class="actions">
        <el-button v-if="busy" type="warning" plain @click="stop">停止</el-button>
        <el-button
          type="primary"
          :icon="Promotion"
          :disabled="busy || !input.trim()"
          @click="send"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  max-width: 860px;
  margin: 0 auto;
}
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
}
.empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.row {
  display: flex;
  gap: 10px;
  margin: 12px 8px;
  align-items: flex-start;
}
.row.user {
  flex-direction: row-reverse;
}
.avatar {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
}
.row.assistant .avatar {
  background: var(--el-color-primary);
}
.row.user .avatar {
  background: var(--el-color-success);
}
.bubble {
  max-width: 76%;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--el-fill-color-light);
  word-break: break-word;
}
.row.user .bubble {
  background: var(--el-color-primary-light-8);
}
.text {
  white-space: pre-wrap;
  line-height: 1.6;
}
.caret {
  color: var(--el-color-primary);
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
.no-evidence {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.refs {
  margin-top: 10px;
  border-top: 1px dashed var(--el-border-color);
  padding-top: 8px;
}
.ref-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.ref-card {
  margin-bottom: 6px;
  background: var(--el-bg-color);
}
.ref-head {
  display: flex;
  gap: 8px;
  align-items: baseline;
  font-size: 12px;
}
.ref-index {
  color: var(--el-color-primary);
  font-weight: 600;
}
.ref-doc {
  font-weight: 600;
}
.ref-sec {
  color: var(--el-text-color-secondary);
}
.ref-snippet {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.composer {
  padding-top: 12px;
}
.actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
</style>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'

import { askStream } from '../api/client'
import { useChat } from '../stores/chat'
import type { ChatTurn } from '../types'

// 会话状态由 store 持有(切路由不丢),这里只负责渲染与滚动
const { messages, input, busy, controller, pushMessage } = useChat()
const listEl = ref<HTMLElement | null>(null)

async function scrollBottom(): Promise<void> {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

// 内容一变就跟随到底:推流逐字增长、以及换页回来恢复历史都靠它
watch(messages, () => void scrollBottom(), { deep: true })
onMounted(() => void scrollBottom())

async function send(): Promise<void> {
  const query = input.value.trim()
  if (!query || busy.value) return
  input.value = ''

  // 先把已有的对话作为历史(必须在把本次提问推进列表之前取,否则会重复)
  const history: ChatTurn[] = messages.value
    .filter((m) => m.text)
    .map((m) => ({ role: m.role, content: m.text }))

  pushMessage('user', query)
  const bot = pushMessage('assistant')
  bot.streaming = true
  busy.value = true
  controller.value = new AbortController()

  try {
    await askStream(
      query,
      history,
      (text) => {
        bot.text += text
      },
      (done) => {
        bot.streaming = false
        bot.noEvidence = done.no_evidence
        bot.text = done.answer
      },
      controller.value.signal,
    )
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      ElMessage.error(`请求出错:${(e as Error).message}`)
    }
  } finally {
    // 组件可能已在中途被卸载(切去了文档管理),这里读写的都是 store 里的共享状态,
    // 不受组件卸载影响;滚动交给 watch,listEl 已销毁也无妨。
    bot.streaming = false
    busy.value = false
    controller.value = null
  }
}

function stop(): void {
  controller.value?.abort()
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
          <div v-if="m.role === 'assistant' && !m.streaming && m.noEvidence" class="no-evidence">
            本次未检索到足够证据,未生成基于文档的回答。
          </div>
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
.composer {
  padding-top: 12px;
}
.actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
</style>

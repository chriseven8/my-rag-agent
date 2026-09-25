import { ref, shallowRef } from 'vue'

export interface Message {
  role: 'user' | 'assistant'
  text: string
  noEvidence: boolean
  streaming: boolean
}

/**
 * 会话状态放在模块作用域,而不是组件的 setup() 里。
 *
 * 切路由(对话问答 ↔ 文档管理)会卸载并重建视图组件:状态挂在组件上就跟着实例一起没了,
 * 于是"看完文档管理再回来,对话全没了"。放在这里则整个页面生命周期内共享,
 * 组件只是这份状态的一个视图 —— 而且推流途中的请求也会继续把结果写回来,
 * 切走再回来能看到它已经答完。
 */
const messages = ref<Message[]>([])
const input = ref('')
const busy = ref(false)
// AbortController 不需要响应式,用 shallowRef 避免被深层代理
const controller = shallowRef<AbortController | null>(null)

export function useChat() {
  function pushMessage(role: Message['role'], text = ''): Message {
    messages.value.push({ role, text, noEvidence: false, streaming: false })
    // 必须再按下标读一次,拿回来的是 Vue 包好的响应式代理。
    // 若直接 return 传进去的那个字面量对象,后续 bot.text += delta 是在裸对象上赋值,
    // 绕过 set 拦截器 → 不触发重渲染 → 整段回答要等请求结束才一次性刷出。
    return messages.value[messages.value.length - 1]
  }

  return { messages, input, busy, controller, pushMessage }
}

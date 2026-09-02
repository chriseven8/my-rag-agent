<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type TagProps, type UploadRequestOptions } from 'element-plus'
import { Refresh, UploadFilled } from '@element-plus/icons-vue'

import { deleteDoc, listDocs, uploadDoc } from '../api/client'
import type { DocRecord, DocStatus } from '../types'

const docs = ref<DocRecord[]>([])
const loading = ref(false)

const STATUS_TAG: Record<DocStatus, { type: TagProps['type']; label: string }> = {
  processing: { type: 'warning', label: '解析中' },
  ready: { type: 'success', label: '已就绪' },
  failed: { type: 'danger', label: '失败' },
}

async function refresh(): Promise<void> {
  loading.value = true
  try {
    docs.value = await listDocs()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function waitReady(docId: string): Promise<void> {
  // 上传后后台异步解析,轮询直到该文档不再是 processing
  for (let i = 0; i < 20; i++) {
    await new Promise((resolve) => setTimeout(resolve, 500))
    const fresh = await listDocs().catch(() => null)
    const rec = fresh?.find((d) => d.doc_id === docId)
    if (!rec || rec.status !== 'processing') return
  }
}

async function handleUpload(opts: UploadRequestOptions): Promise<void> {
  try {
    const { doc_id } = await uploadDoc(opts.file)
    opts.onSuccess({ doc_id })
    ElMessage.success(`已上传「${opts.file.name}」,开始解析`)
    await refresh()
    await waitReady(doc_id)
    await refresh()
  } catch (e) {
    ElMessage.error(`上传失败:${(e as Error).message}`)
    // 满足 el-upload 约定的错误回调(状态等字段与错误体无关,补默认值)
    opts.onError({
      name: (e as Error).name,
      message: (e as Error).message,
      status: 0,
      method: 'POST',
      url: '/api/documents/upload',
    } as unknown as Parameters<typeof opts.onError>[0])
  }
}

async function handleDelete(row: DocRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除「${row.doc_name}」吗?对应向量与索引会一并清理。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return // 用户取消
  }
  try {
    await deleteDoc(row.doc_id)
    ElMessage.success('已删除')
    await refresh()
  } catch (e) {
    ElMessage.error(`删除失败:${(e as Error).message}`)
  }
}

onMounted(refresh)
</script>

<template>
  <div class="documents-view">
    <div class="toolbar">
      <h3 class="title">文档管理</h3>
      <el-button :icon="Refresh" circle title="刷新" @click="refresh" />
    </div>

    <el-upload
      class="uploader"
      drag
      multiple
      :show-file-list="false"
      :http-request="handleUpload"
      accept=".md,.txt"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">把文档拖到此处,或 <em>点击上传</em></div>
      <template #tip>
        <div class="el-upload__tip">支持 Markdown / 纯文本(.md/.txt),上传后自动切分并入库。</div>
      </template>
    </el-upload>

    <el-table v-loading="loading" :data="docs" class="table" empty-text="暂无文档">
      <el-table-column prop="doc_name" label="文件名" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG[(row as DocRecord).status].type">
            {{ STATUS_TAG[(row as DocRecord).status].label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上传时间" min-width="180">
        <template #default="{ row }">
          {{ (row as DocRecord).created_at.replace('T', ' ').slice(0, 19) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" link @click="handleDelete(row as DocRecord)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.documents-view {
  max-width: 980px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  margin: 4px 0;
}
.uploader {
  margin-bottom: 16px;
}
.table {
  width: 100%;
}
</style>

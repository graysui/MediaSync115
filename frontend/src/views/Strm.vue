<template>
  <div class="strm-page">
    <div class="page-header">
      <div>
        <h2>STRM 设置</h2>
        <p class="page-subtitle">保留原有归档输出目录生成逻辑，额外支持临时指定一个 115 源目录并手动运行。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="refreshing" @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <el-card class="section-card">
      <template #header>
        <div class="card-title-row">
          <span class="card-title">STRM 配置</span>
          <div class="status-tags">
            <el-tag :type="config.strm_enabled ? 'success' : 'info'">
              {{ config.strm_enabled ? '已启用' : '未启用' }}
            </el-tag>
            <el-tag :type="runtime.generate_running ? 'warning' : 'info'">
              {{ runtime.generate_running ? '运行中' : '空闲' }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-form label-width="150px" class="config-form">
        <div class="config-grid">
          <el-form-item label="启用 STRM">
            <el-switch v-model="config.strm_enabled" />
          </el-form-item>

          <el-form-item label="播放模式">
            <el-select v-model="config.strm_redirect_mode" style="width: 220px">
              <el-option label="自动（推荐）" value="auto" />
              <el-option label="302 直链播放" value="redirect" />
              <el-option label="服务端代理" value="proxy" />
            </el-select>
          </el-form-item>

          <el-form-item label="生成后刷新 Emby">
            <el-switch v-model="config.strm_refresh_emby_after_generate" />
          </el-form-item>

          <el-form-item label="生成后刷新飞牛">
            <el-switch v-model="config.strm_refresh_feiniu_after_generate" />
          </el-form-item>

          <el-form-item label="STRM 输出目录" class="grid-span-2">
            <el-select
              v-model="config.strm_output_dir"
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入目录路径"
              style="width: 100%"
            >
              <el-option
                v-for="item in mountPaths"
                :key="item.path"
                :label="item.writable ? `${item.path}（${item.label}，可写）` : `${item.path}（${item.label}，不可写）`"
                :value="item.path"
                :disabled="!item.writable"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="播放根地址" class="grid-span-2">
            <el-input
              v-model="config.strm_base_url"
              :placeholder="suggestedBaseUrl || '例如：http://192.168.1.100:9008'"
            />
          </el-form-item>

          <el-form-item label="代理模式">
            <el-switch v-model="config.strm_proxy_enabled" />
          </el-form-item>

          <el-form-item v-if="config.strm_proxy_enabled" label="代理端口">
            <el-input-number v-model="config.strm_proxy_port" :min="1024" :max="65535" :step="1" style="width: 160px" />
          </el-form-item>
        </div>

        <div class="config-actions">
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
          <el-button :loading="diagnosing" @click="diagnoseStrm">STRM 诊断</el-button>
        </div>
      </el-form>
    </el-card>

    <el-card class="section-card">
      <template #header>
        <div class="card-title-row">
          <span class="card-title">生成操作</span>
          <div class="status-tags">
            <el-tag :type="runtime.queue_waiting_count > 0 ? 'warning' : 'info'">队列 {{ runtime.queue_waiting_count }}</el-tag>
            <el-tag :type="runtime.active_task ? 'success' : 'info'">当前 {{ activeTaskText }}</el-tag>
          </div>
        </div>
      </template>

      <div class="source-block">
        <div class="source-meta">
          <div class="source-title">临时指定源目录</div>
          <div class="source-subtitle">只保存在浏览器本地，刷新页面后仍保留，手动清空后移除。</div>
        </div>

        <div class="source-row">
          <el-tag v-if="sourceDir.cid" closable type="info" @close="clearSourceDir">
            {{ sourceDir.name || sourceDir.cid }}
          </el-tag>
          <el-button @click="openPicker">选择目录</el-button>
          <el-button :disabled="!sourceDir.cid" @click="clearSourceDir">清空</el-button>
        </div>
      </div>

      <div class="config-actions">
        <el-button type="primary" :disabled="!sourceDir.cid" :loading="generatingSource" @click="generateSourceFiles">指定源生成</el-button>
      </div>

      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">归档输出目录</span>
          <span class="status-value">{{ config.archive_output_name || config.archive_output_cid || '未配置' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">临时源目录</span>
          <span class="status-value">{{ sourceDir.name || sourceDir.cid || '未选择' }}</span>
        </div>
        <div class="status-item status-item-full">
          <span class="status-label">队列顺序</span>
          <span class="status-value">{{ runtime.queue_waiting_count > 0 ? `前方还有 ${runtime.queue_waiting_count} 个任务等待` : '当前没有等待中的任务' }}</span>
        </div>
        <div class="status-item status-item-full">
          <span class="status-label">当前任务</span>
          <span class="status-value">{{ activeTaskText }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">开始时间</span>
          <span class="status-value">{{ runtime.last_generate_started_at ? formatBeijingTableCell(null, null, runtime.last_generate_started_at) : '-' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">结束时间</span>
          <span class="status-value">{{ runtime.last_generate_finished_at ? formatBeijingTableCell(null, null, runtime.last_generate_finished_at) : '-' }}</span>
        </div>
        <div class="status-item status-item-full">
          <span class="status-label">最近结果</span>
          <span class="status-value">{{ summaryText }}</span>
        </div>
        <div v-if="runtime.last_generate_error" class="status-item status-item-full">
          <span class="status-label">失败原因</span>
          <span class="status-value status-error">{{ runtime.last_generate_error }}</span>
        </div>
      </div>
    </el-card>

    <el-card v-if="diagnosis" class="section-card">
      <template #header>
        <div class="card-title">STRM 诊断</div>
      </template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="样本文件">
          <span class="break-all">{{ diagnosis.sample_file || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="当前 UA">
          <span class="break-all">{{ diagnosis.player_user_agent || '空' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="配置模式">{{ getModeLabel(diagnosis.configured_mode) }}</el-descriptions-item>
        <el-descriptions-item label="实际模式">{{ getModeLabel(diagnosis.effective_mode) }}</el-descriptions-item>
        <el-descriptions-item label="115 要求">{{ getRequirementLabel(diagnosis.direct_requirement) }}</el-descriptions-item>
        <el-descriptions-item label="直链探测">{{ getProbeText(diagnosis.direct_probe) }}</el-descriptions-item>
        <el-descriptions-item label="样本链接">
          <span class="break-all">{{ diagnosis.sample_url || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="115 直链">
          <span class="break-all">{{ diagnosis.download_url || '-' }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <el-alert :closable="false" type="info" show-icon class="diagnosis-alert" :title="diagnosis.reason || '诊断完成'" :description="diagnosis.note || ''" />
    </el-card>

    <el-dialog v-model="pickerVisible" title="选择 115 源目录" width="520px" :close-on-click-modal="false">
      <div class="picker-breadcrumb">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item v-for="crumb in pickerBreadcrumbs" :key="crumb.cid">
            <a @click.prevent="navigatePicker(crumb.cid)">{{ getFolderDisplayName(crumb) }}</a>
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <div class="picker-toolbar">
        <el-button size="small" :loading="pickerCreating" @click="createPickerFolder">新建文件夹</el-button>
      </div>

      <el-table
        :data="pickerFolders"
        v-loading="pickerLoading"
        size="small"
        max-height="400px"
        @row-click="handlePickerRowClick"
      >
        <el-table-column label="文件夹名称" min-width="300">
          <template #default="{ row }">
            <span>{{ getFolderDisplayName(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="cid" label="CID" width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" text @click.stop="enterPickerFolder(row)">进入</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <div class="picker-footer">
          <span>当前目录 CID: {{ pickerCurrentCid }}</span>
          <div>
            <el-button @click="pickerVisible = false">取消</el-button>
            <el-button type="primary" @click="confirmPicker">选择当前目录</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { archiveApi, pan115Api, strmApi } from '@/api'
import { formatBeijingTableCell } from '@/utils/timezone'

const refreshing = ref(false)
const saving = ref(false)
const generatingSource = ref(false)
const diagnosing = ref(false)
const mountPaths = ref([])
const suggestedBaseUrl = ref('')
const diagnosis = ref(null)
let pollingTimer = null

const pickerVisible = ref(false)
const pickerFolders = ref([])
const pickerLoading = ref(false)
const pickerCreating = ref(false)
const pickerCurrentCid = ref('0')
const pickerHistory = ref([])
const pickerBreadcrumbs = computed(() => [{ cid: '0', name: '根目录' }, ...pickerHistory.value])

const sourceDir = reactive({
  cid: localStorage.getItem('mediasync115.strm.source_cid') || '',
  name: localStorage.getItem('mediasync115.strm.source_name') || ''
})

const config = reactive({
  strm_enabled: false,
  strm_output_dir: '',
  strm_base_url: '',
  strm_redirect_mode: 'auto',
  strm_refresh_emby_after_generate: false,
  strm_refresh_feiniu_after_generate: false,
  strm_proxy_enabled: false,
  strm_proxy_port: 8099,
  archive_output_cid: '',
  archive_output_name: ''
})

const runtime = reactive({
  generate_running: false,
  queue_waiting_count: 0,
  active_task: null,
  last_generate_started_at: '',
  last_generate_finished_at: '',
  last_generate_error: '',
  last_generate_summary: null,
  last_generate_trigger: ''
})

const activeTaskText = computed(() => {
  const task = runtime.active_task
  if (!task) return '无'
  if (task.mode === 'source') {
    return `指定源 ${task.source_name || task.source_cid || '-'}`
  }
  return `归档输出目录 ${task.output_cid || '-'}`
})

const summaryText = computed(() => {
  const summary = runtime.last_generate_summary
  if (!summary) return '暂无生成记录'
  return `扫描 ${summary.scanned_video_count || 0} 个视频，写入 ${summary.written_count || 0} 个，未变更 ${summary.unchanged_count || 0} 个，删除 ${summary.removed_count || 0} 个`
})

const getModeLabel = (mode) => {
  if (mode === 'redirect') return '302 直链播放'
  if (mode === 'proxy') return '服务端代理'
  return '自动（推荐）'
}

const getRequirementLabel = (requirement) => {
  if (requirement === '1') return 'f=1，需要绑定 User-Agent'
  if (requirement === '3') return 'f=3，需要额外 Cookie'
  return '无特殊要求'
}

const getProbeText = (probe) => {
  if (!probe) return '-'
  if (!probe.ok) {
    return probe.status_code ? `失败 (${probe.status_code})` : `失败 (${probe.error || '未知错误'})`
  }
  const sizeText = probe.content_length ? `，长度 ${probe.content_length}` : ''
  return `成功 (${probe.status_code}${sizeText})`
}

const applyConfig = (data) => {
  const wasGenerating = runtime.generate_running || generatingSource.value

  config.strm_enabled = !!data.strm_enabled
  config.strm_output_dir = data.strm_output_dir || ''
  config.strm_base_url = data.strm_base_url || ''
  config.strm_redirect_mode = data.strm_redirect_mode || 'auto'
  config.strm_refresh_emby_after_generate = !!data.strm_refresh_emby_after_generate
  config.strm_refresh_feiniu_after_generate = !!data.strm_refresh_feiniu_after_generate
  config.strm_proxy_enabled = !!data.strm_proxy_enabled
  config.strm_proxy_port = Number(data.strm_proxy_port) || 8099
  config.archive_output_cid = data.archive_output_cid || ''
  config.archive_output_name = data.archive_output_name || ''
  mountPaths.value = Array.isArray(data.mount_paths) ? data.mount_paths : []
  suggestedBaseUrl.value = data.suggested_base_url || ''

  const nextRuntime = data.runtime || {}
  runtime.generate_running = !!nextRuntime.generate_running
  runtime.queue_waiting_count = Number(nextRuntime.queue_waiting_count) || 0
  runtime.active_task = nextRuntime.active_task || null
  runtime.last_generate_started_at = nextRuntime.last_generate_started_at || ''
  runtime.last_generate_finished_at = nextRuntime.last_generate_finished_at || ''
  runtime.last_generate_error = nextRuntime.last_generate_error || ''
  runtime.last_generate_summary = nextRuntime.last_generate_summary || null
  runtime.last_generate_trigger = nextRuntime.last_generate_trigger || ''

  generatingSource.value = runtime.generate_running && runtime.active_task?.mode === 'source'

  if (wasGenerating && !runtime.generate_running) {
    if (runtime.last_generate_error) {
      ElMessage.error(runtime.last_generate_error)
    } else if (runtime.last_generate_summary) {
      ElMessage.success('STRM 生成完成')
    }
  }
}

const loadConfig = async () => {
  const { data } = await strmApi.getConfig()
  applyConfig(data)
  setupPolling()
}

const refreshAll = async () => {
  refreshing.value = true
  try {
    await loadConfig()
  } finally {
    refreshing.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const { data } = await strmApi.updateConfig({
      strm_enabled: config.strm_enabled,
      strm_output_dir: config.strm_output_dir,
      strm_base_url: config.strm_base_url,
      strm_redirect_mode: config.strm_redirect_mode,
      strm_refresh_emby_after_generate: config.strm_refresh_emby_after_generate,
      strm_refresh_feiniu_after_generate: config.strm_refresh_feiniu_after_generate,
      strm_proxy_enabled: config.strm_proxy_enabled,
      strm_proxy_port: config.strm_proxy_port
    })
    applyConfig(data)
    ElMessage.success('STRM 配置已保存')
  } finally {
    saving.value = false
  }
}

const clearSourceDir = () => {
  sourceDir.cid = ''
  sourceDir.name = ''
  localStorage.removeItem('mediasync115.strm.source_cid')
  localStorage.removeItem('mediasync115.strm.source_name')
}

const generateSourceFiles = async () => {
  if (!sourceDir.cid) {
    ElMessage.warning('请先选择指定源目录')
    return
  }
  localStorage.setItem('mediasync115.strm.source_cid', sourceDir.cid || '')
  localStorage.setItem('mediasync115.strm.source_name', sourceDir.name || '')
  generatingSource.value = true
  try {
    const { data } = await strmApi.generate({
      source_cid: sourceDir.cid,
      source_name: sourceDir.name
    })
    ElMessage.success(data.message || '指定源 STRM 任务已提交')
    await loadConfig()
  } finally {
    generatingSource.value = false
  }
}

const getFolderDisplayName = (folder) => {
  if (!folder || typeof folder !== 'object') return '-'
  return String(
    folder.name
    || folder.n
    || folder.fn
    || folder.folder_name
    || folder.file_name
    || folder.cid
    || '-'
  ).trim() || '-'
}

const getCurrentFolderName = () => {
  if (pickerCurrentCid.value === '0') return '根目录'
  const found = pickerHistory.value.find(h => h.cid === pickerCurrentCid.value)
  return getFolderDisplayName(found) || pickerCurrentCid.value
}

const openPicker = () => {
  pickerCurrentCid.value = '0'
  pickerHistory.value = []
  pickerFolders.value = []
  pickerVisible.value = true
  loadPickerFolders('0')
}

const loadPickerFolders = async (cid) => {
  pickerLoading.value = true
  pickerCurrentCid.value = cid
  try {
    const { data } = await archiveApi.listFolders(cid)
    pickerFolders.value = (Array.isArray(data?.folders) ? data.folders : []).map(folder => ({
      cid: String(folder.cid || ''),
      name: getFolderDisplayName(folder)
    }))
  } catch {
    pickerFolders.value = []
  } finally {
    pickerLoading.value = false
  }
}

const navigatePicker = (cid) => {
  if (cid === pickerCurrentCid.value) return
  const index = pickerHistory.value.findIndex(h => h.cid === cid)
  if (index >= 0) pickerHistory.value = pickerHistory.value.slice(0, index)
  else if (cid === '0') pickerHistory.value = []
  loadPickerFolders(cid)
}

const handlePickerRowClick = (row) => {
  enterPickerFolder(row)
}

const enterPickerFolder = (row) => {
  const rowName = getFolderDisplayName(row)
  const currentName = getCurrentFolderName()
  if (pickerCurrentCid.value !== '0' && !pickerHistory.value.find(h => h.cid === pickerCurrentCid.value)) {
    pickerHistory.value.push({ cid: pickerCurrentCid.value, name: currentName })
  }
  if (!pickerHistory.value.find(h => h.cid === row.cid)) {
    pickerHistory.value.push({ cid: row.cid, name: rowName })
  }
  loadPickerFolders(row.cid)
}

const createPickerFolder = async () => {
  try {
    const { value } = await ElMessageBox.prompt('请输入新文件夹名称', '新建文件夹', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '文件夹名称不能为空'
    })

    const folderName = String(value || '').trim()
    if (!folderName) return

    pickerCreating.value = true
    await pan115Api.createFolder(pickerCurrentCid.value, folderName)
    ElMessage.success(`已创建文件夹：${folderName}`)
    await loadPickerFolders(pickerCurrentCid.value)
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  } finally {
    pickerCreating.value = false
  }
}

const confirmPicker = () => {
  sourceDir.cid = pickerCurrentCid.value
  sourceDir.name = getCurrentFolderName()
  localStorage.setItem('mediasync115.strm.source_cid', sourceDir.cid || '')
  localStorage.setItem('mediasync115.strm.source_name', sourceDir.name || '')
  pickerVisible.value = false
  ElMessage.success('目录已选择')
}

const diagnoseStrm = async () => {
  diagnosing.value = true
  try {
    const { data } = await strmApi.diagnose()
    diagnosis.value = data || null
    ElMessage.success('STRM 诊断完成')
  } finally {
    diagnosing.value = false
  }
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const setupPolling = () => {
  stopPolling()
  if (!runtime.generate_running && runtime.queue_waiting_count <= 0 && !runtime.active_task) return
  pollingTimer = setInterval(async () => {
    try {
      const { data } = await strmApi.getConfig()
      applyConfig(data)
      if (!data.runtime?.generate_running && Number(data.runtime?.queue_waiting_count || 0) <= 0 && !data.runtime?.active_task) {
        stopPolling()
      }
    } catch {
      stopPolling()
    }
  }, 4000)
}

onMounted(loadConfig)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.strm-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
}

.page-subtitle {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.section-card {
  border-radius: 8px;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-title {
  font-weight: 600;
}

.status-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
}

.grid-span-2 {
  grid-column: span 2;
}

.config-actions {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.source-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.source-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-title {
  font-weight: 600;
}

.source-subtitle,
.status-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.source-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 20px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.status-item-full {
  grid-column: span 2;
}

.status-value {
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  word-break: break-word;
}

.status-error {
  color: var(--el-color-danger);
}

.break-all {
  word-break: break-all;
}

.diagnosis-alert {
  margin-top: 12px;
}

.picker-breadcrumb {
  margin-bottom: 12px;
}

.picker-toolbar {
  margin-bottom: 12px;
}

.picker-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions :deep(.el-button) {
    flex: 1;
  }

  .config-grid,
  .status-grid {
    grid-template-columns: 1fr;
  }

  .grid-span-2,
  .status-item-full {
    grid-column: span 1;
  }
}
</style>

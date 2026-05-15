<template>
  <div class="archive-page">
    <div class="page-header">
      <div>
        <h2>归档刮削</h2>
        <p class="page-subtitle">自动扫描 115 网盘离线目录，识别影片并按电影/剧集 + 类型归档到分类文件夹。为降低 115 风控概率，扫描会按低频模式顺序执行。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="refreshing" @click="refreshAll">刷新</el-button>
        <el-button type="primary" :loading="scanLoading" @click="runScan">立即扫描</el-button>
      </div>
    </div>

    <el-card class="section-card">
      <template #header>
        <div class="card-title">归档配置</div>
      </template>

      <el-form label-width="140px" class="config-form">
        <div class="config-grid">
          <el-form-item label="启用归档">
            <el-switch v-model="config.archive_enabled" />
          </el-form-item>
          <el-form-item label="转存后自动归档">
            <el-switch v-model="config.archive_auto_on_transfer" />
            <div class="form-hint">转存分享链接成功后自动触发归档扫描</div>
          </el-form-item>
          <el-form-item label="离线完成后自动归档">
            <el-switch v-model="config.archive_auto_on_offline" />
            <div class="form-hint">离线下载完成后自动触发归档扫描</div>
          </el-form-item>
          <el-form-item label="离线监控间隔">
            <el-input-number v-model="config.offline_monitor_interval_minutes" :min="1" :max="60" />
            <span class="suffix-text">分钟</span>
          </el-form-item>
          <el-form-item label="兜底扫描间隔">
            <el-input-number v-model="config.archive_interval_minutes" :min="1" :max="1440" />
            <span class="suffix-text">分钟</span>
          </el-form-item>

          <el-form-item label="115 监听目录" class="grid-span-2">
            <div class="folder-row">
              <el-tag v-if="config.archive_watch_cid" closable type="info" @close="config.archive_watch_cid = ''; config.archive_watch_name = ''">
                {{ config.archive_watch_name || config.archive_watch_cid }}
              </el-tag>
              <el-button size="small" @click="openPicker('watch')">选择目录</el-button>
            </div>
            <div class="form-hint">离线下载完成的影视文件所在目录（只读扫描）</div>
          </el-form-item>

          <el-form-item label="115 输出目录" class="grid-span-2">
            <div class="folder-row">
              <el-tag v-if="config.archive_output_cid" closable type="info" @close="config.archive_output_cid = ''; config.archive_output_name = ''">
                {{ config.archive_output_name || config.archive_output_cid }}
              </el-tag>
              <el-button size="small" @click="openPicker('output')">选择目录</el-button>
            </div>
            <div class="form-hint">归档后的文件将整理到此目录下的 电影/剧集 子目录中</div>
          </el-form-item>
        </div>

        <div class="config-actions">
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
        </div>
      </el-form>
    </el-card>

    <el-card class="section-card">
      <template #header>
        <div class="card-title-row">
          <div class="card-title">命名模板</div>
          <el-button type="primary" :loading="namingSaving" @click="saveNaming">保存命名</el-button>
        </div>
      </template>

      <el-form label-width="140px" class="config-form">
        <div class="config-grid">
          <el-form-item label="电影根目录">
            <el-input v-model="namingConfig.movie_root_dir" />
            <div class="form-hint">示例：{{ namingPreview.movieRoot }}</div>
          </el-form-item>
          <el-form-item label="剧集根目录">
            <el-input v-model="namingConfig.tv_root_dir" />
            <div class="form-hint">示例：{{ namingPreview.tvRoot }}</div>
          </el-form-item>
          <el-form-item label="季目录模板">
            <el-input v-model="namingConfig.season_dir_template" />
            <div class="form-hint">变量：season。预览：{{ namingPreview.seasonDir }}</div>
          </el-form-item>
          <el-form-item label="电影文件模板">
            <el-input v-model="namingConfig.movie_filename_template" />
            <div class="form-hint">变量：title、year、tmdb_id、ext。预览：{{ namingPreview.movieFile }}</div>
          </el-form-item>
          <el-form-item label="剧集文件模板" class="grid-span-2">
            <el-input v-model="namingConfig.tv_filename_template" />
            <div class="form-hint">变量：title、year、tmdb_id、season、episode、ext。预览：{{ namingPreview.tvFile }}</div>
          </el-form-item>
        </div>
      </el-form>
    </el-card>

    <el-card class="section-card">
      <template #header>
        <div class="card-title-row">
          <div class="card-title">分类规则</div>
          <el-button type="primary" :loading="classificationSaving" @click="saveClassification">保存规则</el-button>
        </div>
      </template>

      <el-tabs v-model="classificationTab">
        <el-tab-pane label="电影" name="movie">
          <div class="rules-toolbar">
            <el-button size="small" type="primary" @click="addRule('movie')">新增电影规则</el-button>
          </div>
          <draggable
            v-model="classificationConfig.movie_rules"
            item-key="_key"
            handle=".drag-handle"
            class="rules-list"
          >
            <template #item="{ element, index }">
              <div class="rule-row">
                <span class="drag-handle">拖动</span>
                <el-input v-model="element.name" placeholder="分类目录名" class="rule-name" />
                <el-select v-model="element.match_type" class="rule-type" @change="handleRuleTypeChange(element)">
                  <el-option label="类型" value="genre" />
                  <el-option label="国家/地区" value="country" />
                  <el-option label="兜底" value="default" />
                </el-select>
                <el-select
                  v-if="element.match_type !== 'default'"
                  v-model="element.values"
                  multiple
                  filterable
                  collapse-tags
                  class="rule-values"
                  placeholder="选择匹配值"
                >
                  <el-option
                    v-for="option in getRuleOptions('movie', element.match_type)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
                <span v-else class="rule-values muted-text">第一个兜底规则会在其他规则未命中时生效</span>
                <el-button type="danger" text @click="removeRule('movie', index)">删除</el-button>
              </div>
            </template>
          </draggable>
        </el-tab-pane>

        <el-tab-pane label="剧集" name="tv">
          <div class="rules-toolbar">
            <el-button size="small" type="primary" @click="addRule('tv')">新增剧集规则</el-button>
          </div>
          <draggable
            v-model="classificationConfig.tv_rules"
            item-key="_key"
            handle=".drag-handle"
            class="rules-list"
          >
            <template #item="{ element, index }">
              <div class="rule-row">
                <span class="drag-handle">拖动</span>
                <el-input v-model="element.name" placeholder="分类目录名" class="rule-name" />
                <el-select v-model="element.match_type" class="rule-type" @change="handleRuleTypeChange(element)">
                  <el-option label="类型" value="genre" />
                  <el-option label="国家/地区" value="country" />
                  <el-option label="兜底" value="default" />
                </el-select>
                <el-select
                  v-if="element.match_type !== 'default'"
                  v-model="element.values"
                  multiple
                  filterable
                  collapse-tags
                  class="rule-values"
                  placeholder="选择匹配值"
                >
                  <el-option
                    v-for="option in getRuleOptions('tv', element.match_type)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
                <span v-else class="rule-values muted-text">第一个兜底规则会在其他规则未命中时生效</span>
                <el-button type="danger" text @click="removeRule('tv', index)">删除</el-button>
              </div>
            </template>
          </draggable>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-card class="section-card">
      <template #header>
        <div class="card-title">运行状态</div>
      </template>

      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">归档状态</span>
          <el-tag :type="config.archive_enabled ? 'success' : 'info'">{{ config.archive_enabled ? '已启用' : '未启用' }}</el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">监听目录</span>
          <span class="status-value">{{ config.archive_watch_name || config.archive_watch_cid || '未配置' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">输出目录</span>
          <span class="status-value">{{ config.archive_output_name || config.archive_output_cid || '未配置' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">扫描间隔</span>
          <span class="status-value">{{ config.archive_interval_minutes }} 分钟</span>
        </div>
        <div class="status-item">
          <span class="status-label">扫描任务</span>
          <el-tag :type="runtime.scan_running ? 'warning' : 'info'">{{ runtime.scan_running ? '执行中' : '空闲' }}</el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">最近触发</span>
          <span class="status-value">{{ runtime.last_scan_trigger || '-' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">开始时间</span>
          <span class="status-value">{{ runtime.last_scan_started_at ? formatBeijingTableCell(null, null, runtime.last_scan_started_at) : '-' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">结束时间</span>
          <span class="status-value">{{ runtime.last_scan_finished_at ? formatBeijingTableCell(null, null, runtime.last_scan_finished_at) : '-' }}</span>
        </div>
        <div class="status-item status-item-full">
          <span class="status-label">最近结果</span>
          <span class="status-value">{{ scanSummaryText }}</span>
        </div>
        <div v-if="runtime.last_scan_error" class="status-item status-item-full">
          <span class="status-label">失败原因</span>
          <span class="status-value status-error">{{ runtime.last_scan_error }}</span>
        </div>
      </div>
    </el-card>

    <el-card class="section-card">
      <template #header>
        <div class="tasks-header">
          <div class="card-title">归档任务</div>
          <div class="tasks-toolbar">
            <el-select v-model="filters.status" clearable placeholder="全部状态" class="status-filter" @change="handleFilterChange">
              <el-option label="处理中" value="processing" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
              <el-option label="跳过" value="skipped" />
            </el-select>
            <el-button @click="clearFinished(false)">清理已完成</el-button>
            <el-button type="danger" plain @click="clearFinished(true)">清理含失败</el-button>
          </div>
        </div>
      </template>

      <div class="table-wrap">
        <el-table :data="tasks" v-loading="tasksLoading" size="small">
          <el-table-column prop="created_at" label="时间" min-width="170" :formatter="formatBeijingTableCell" />
          <el-table-column prop="source_filename" label="源文件" min-width="220" show-overflow-tooltip />
          <el-table-column label="类型" width="90">
            <template #default="{ row }">{{ mediaTypeLabel(row.media_type) }}</template>
          </el-table-column>
          <el-table-column prop="tmdb_title" label="识别结果" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.tmdb_title || '-' }}</span>
              <span v-if="row.tmdb_year" class="year-text">({{ row.tmdb_year }})</span>
            </template>
          </el-table-column>
          <el-table-column prop="genre_name" label="分类" width="130" show-overflow-tooltip />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_path" label="目标路径" min-width="260" show-overflow-tooltip />
          <el-table-column prop="error_message" label="错误原因" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'failed'" type="primary" text @click="retryTask(row)">重试</el-button>
              <span v-else class="muted-text">-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager-wrap">
        <el-pagination
          background
          layout="prev, pager, next, jumper, total"
          :total="total"
          :current-page="filters.page"
          :page-size="filters.limit"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="pickerVisible" :title="pickerTitle" width="520px" :close-on-click-modal="false">
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

      <el-table :data="pickerFolders" v-loading="pickerLoading" size="small" max-height="400px" @row-click="handlePickerRowClick">
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
import draggable from 'vuedraggable'
import { archiveApi, pan115Api } from '@/api'
import { TMDB_COUNTRIES, TMDB_MOVIE_GENRES, TMDB_TV_GENRES } from '@/utils/tmdb_constants'
import { formatBeijingTableCell } from '@/utils/timezone'

const refreshing = ref(false)
const saving = ref(false)
const namingSaving = ref(false)
const classificationSaving = ref(false)
const scanLoading = ref(false)
const tasksLoading = ref(false)
const total = ref(0)
const tasks = ref([])
let scanPollingTimer = null

const config = reactive({
  archive_enabled: false,
  archive_watch_cid: '',
  archive_watch_name: '',
  archive_output_cid: '',
  archive_output_name: '',
  archive_interval_minutes: 10,
  archive_auto_on_transfer: true,
  archive_auto_on_offline: true,
  offline_monitor_interval_minutes: 3
})

const runtime = reactive({
  scan_running: false,
  last_scan_started_at: '',
  last_scan_finished_at: '',
  last_scan_trigger: '',
  last_scan_summary: null,
  last_scan_error: ''
})

const namingConfig = reactive({
  movie_root_dir: '电影',
  tv_root_dir: '剧集',
  season_dir_template: '第{{ season }}季',
  movie_filename_template: '{{ title }} ({{ year }}){{ ext }}',
  tv_filename_template: "{{ title }} ({{ year }}) - S{{ '%02d' % season }}E{{ '%02d' % episode }}{{ ext }}"
})

const classificationConfig = reactive({
  movie_rules: [],
  tv_rules: []
})
const classificationTab = ref('movie')
let ruleKeySeed = 1

const filters = reactive({
  status: '',
  page: 1,
  limit: 20
})

const pickerVisible = ref(false)
const pickerTarget = ref('')
const pickerFolders = ref([])
const pickerLoading = ref(false)
const pickerCreating = ref(false)
const pickerCurrentCid = ref('0')
const pickerHistory = ref([])

const pickerTitle = computed(() => pickerTarget.value === 'watch' ? '选择 115 监听目录' : '选择 115 输出目录')
const pickerBreadcrumbs = computed(() => [{ cid: '0', name: '根目录' }, ...pickerHistory.value])

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

// 获取当前目录的名称
const getCurrentFolderName = () => {
  if (pickerCurrentCid.value === '0') return '根目录'
  const found = pickerHistory.value.find(h => h.cid === pickerCurrentCid.value)
  return getFolderDisplayName(found) || pickerCurrentCid.value
}

const mediaTypeLabel = (v) => v === 'movie' ? '电影' : v === 'tv' ? '剧集' : '-'
const statusLabel = (v) => ({ processing: '处理中', success: '成功', failed: '失败', skipped: '跳过' }[v] || '待处理')
const statusTagType = (v) => ({ success: 'success', failed: 'danger', processing: 'warning' }[v] || 'info')
const scanSummaryText = computed(() => {
  const summary = runtime.last_scan_summary
  if (!summary || typeof summary !== 'object') {
    return runtime.scan_running ? '扫描执行中' : '暂无记录'
  }
  return `总计 ${Number(summary.total || 0)} 个，成功 ${Number(summary.success || 0)} 个，跳过 ${Number(summary.skipped || 0)} 个，失败 ${Number(summary.failed || 0)} 个`
})

const renderTemplatePreview = (template, context) => {
  let rendered = String(template || '')
  rendered = rendered.replace(/{{\s*'%02d'\s*%\s*season\s*}}/g, String(context.season).padStart(2, '0'))
  rendered = rendered.replace(/{{\s*'%02d'\s*%\s*episode\s*}}/g, String(context.episode).padStart(2, '0'))
  Object.entries(context).forEach(([key, value]) => {
    rendered = rendered.replace(new RegExp(`{{\\s*${key}\\s*}}`, 'g'), String(value))
  })
  return rendered
}

const namingPreview = computed(() => {
  const context = {
    title: '示例影片',
    year: 2026,
    tmdb_id: 12345,
    season: 1,
    episode: 2,
    ext: '.mkv'
  }
  return {
    movieRoot: namingConfig.movie_root_dir || '电影',
    tvRoot: namingConfig.tv_root_dir || '剧集',
    seasonDir: renderTemplatePreview(namingConfig.season_dir_template, context),
    movieFile: renderTemplatePreview(namingConfig.movie_filename_template, context),
    tvFile: renderTemplatePreview(namingConfig.tv_filename_template, context)
  }
})

const withRuleKeys = (rules) => (Array.isArray(rules) ? rules : []).map(rule => ({
  _key: rule._key || `rule-${ruleKeySeed++}`,
  name: rule.name || '',
  match_type: ['genre', 'country', 'default'].includes(rule.match_type) ? rule.match_type : 'default',
  values: Array.isArray(rule.values) ? [...rule.values] : []
}))

const serializeRules = (rules) => (Array.isArray(rules) ? rules : [])
  .map(rule => ({
    name: String(rule.name || '').trim(),
    match_type: rule.match_type,
    values: rule.match_type === 'default' ? [] : [...(rule.values || [])]
  }))
  .filter(rule => rule.name && ['genre', 'country', 'default'].includes(rule.match_type))

const getRuleOptions = (mediaType, matchType) => {
  if (matchType === 'country') {
    return TMDB_COUNTRIES.map(item => ({ label: `${item.label} (${item.code})`, value: item.code }))
  }
  const genres = mediaType === 'movie' ? TMDB_MOVIE_GENRES : TMDB_TV_GENRES
  return genres.map(item => ({ label: `${item.label} (${item.id})`, value: item.id }))
}

const handleRuleTypeChange = (rule) => {
  rule.values = []
}

const addRule = (type) => {
  const rules = type === 'movie' ? classificationConfig.movie_rules : classificationConfig.tv_rules
  rules.push({
    _key: `rule-${ruleKeySeed++}`,
    name: '',
    match_type: 'default',
    values: []
  })
}

const removeRule = (type, index) => {
  const rules = type === 'movie' ? classificationConfig.movie_rules : classificationConfig.tv_rules
  rules.splice(index, 1)
}

const loadNaming = async () => {
  const { data } = await archiveApi.getNaming()
  namingConfig.movie_root_dir = data.movie_root_dir || '电影'
  namingConfig.tv_root_dir = data.tv_root_dir || '剧集'
  namingConfig.season_dir_template = data.season_dir_template || '第{{ season }}季'
  namingConfig.movie_filename_template = data.movie_filename_template || '{{ title }} ({{ year }}){{ ext }}'
  namingConfig.tv_filename_template = data.tv_filename_template || "{{ title }} ({{ year }}) - S{{ '%02d' % season }}E{{ '%02d' % episode }}{{ ext }}"
}

const loadClassification = async () => {
  const { data } = await archiveApi.getClassification()
  classificationConfig.movie_rules = withRuleKeys(data.movie_rules)
  classificationConfig.tv_rules = withRuleKeys(data.tv_rules)
}

const saveNaming = async () => {
  namingSaving.value = true
  try {
    await archiveApi.updateNaming({
      movie_root_dir: namingConfig.movie_root_dir,
      tv_root_dir: namingConfig.tv_root_dir,
      season_dir_template: namingConfig.season_dir_template,
      movie_filename_template: namingConfig.movie_filename_template,
      tv_filename_template: namingConfig.tv_filename_template
    })
    ElMessage.success('命名模板已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '命名模板保存失败')
  } finally {
    namingSaving.value = false
  }
}

const saveClassification = async () => {
  classificationSaving.value = true
  try {
    await archiveApi.updateClassification({
      movie_rules: serializeRules(classificationConfig.movie_rules),
      tv_rules: serializeRules(classificationConfig.tv_rules)
    })
    ElMessage.success('分类规则已保存')
    await loadClassification()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '分类规则保存失败')
  } finally {
    classificationSaving.value = false
  }
}

const loadConfig = async () => {
  const { data } = await archiveApi.getConfig()
  config.archive_enabled = !!data.archive_enabled
  config.archive_watch_cid = data.archive_watch_cid || ''
  config.archive_watch_name = data.archive_watch_name || ''
  config.archive_output_cid = data.archive_output_cid || ''
  config.archive_output_name = data.archive_output_name || ''
  config.archive_interval_minutes = Number(data.archive_interval_minutes || 10)
  config.archive_auto_on_transfer = data.archive_auto_on_transfer !== false
  config.archive_auto_on_offline = data.archive_auto_on_offline !== false
  config.offline_monitor_interval_minutes = Number(data.offline_monitor_interval_minutes || 3)
  runtime.scan_running = !!data.runtime?.scan_running
  runtime.last_scan_started_at = data.runtime?.last_scan_started_at || ''
  runtime.last_scan_finished_at = data.runtime?.last_scan_finished_at || ''
  runtime.last_scan_trigger = data.runtime?.last_scan_trigger || ''
  runtime.last_scan_summary = data.runtime?.last_scan_summary || null
  runtime.last_scan_error = data.runtime?.last_scan_error || ''
}

const loadTasks = async () => {
  tasksLoading.value = true
  try {
    const { data } = await archiveApi.listTasks({ status: filters.status || undefined, limit: filters.limit, offset: (filters.page - 1) * filters.limit })
    tasks.value = data.items || []
    total.value = Number(data.total || 0)
  } finally {
    tasksLoading.value = false
  }
}

const refreshAll = async () => {
  refreshing.value = true
  try {
    await Promise.all([loadConfig(), loadNaming(), loadClassification(), loadTasks()])
  } catch {
    ElMessage.error('刷新归档信息失败')
  } finally {
    refreshing.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await archiveApi.updateConfig({
      archive_enabled: config.archive_enabled,
      archive_watch_cid: config.archive_watch_cid,
      archive_watch_name: config.archive_watch_name,
      archive_output_cid: config.archive_output_cid,
      archive_output_name: config.archive_output_name,
      archive_interval_minutes: config.archive_interval_minutes,
      archive_auto_on_transfer: config.archive_auto_on_transfer,
      archive_auto_on_offline: config.archive_auto_on_offline,
      offline_monitor_interval_minutes: config.offline_monitor_interval_minutes
    })
    ElMessage.success('归档配置已保存')
  } finally {
    saving.value = false
  }
}

const runScan = async () => {
  scanLoading.value = true
  try {
    const { data } = await archiveApi.runScan()
    runtime.scan_running = !!data.runtime?.scan_running
    runtime.last_scan_started_at = data.runtime?.last_scan_started_at || runtime.last_scan_started_at
    runtime.last_scan_finished_at = data.runtime?.last_scan_finished_at || runtime.last_scan_finished_at
    runtime.last_scan_trigger = data.runtime?.last_scan_trigger || runtime.last_scan_trigger
    runtime.last_scan_summary = data.runtime?.last_scan_summary || null
    runtime.last_scan_error = data.runtime?.last_scan_error || ''
    ElMessage.success(data.message || '归档扫描已启动')
    startScanPolling()
    await loadTasks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '归档扫描失败')
  } finally {
    scanLoading.value = false
  }
}

const stopScanPolling = () => {
  if (scanPollingTimer) {
    clearInterval(scanPollingTimer)
    scanPollingTimer = null
  }
}

const startScanPolling = () => {
  stopScanPolling()
  scanPollingTimer = window.setInterval(async () => {
    try {
      await Promise.all([loadConfig(), loadTasks()])
      if (!runtime.scan_running) {
        stopScanPolling()
        if (runtime.last_scan_error) {
          ElMessage.warning(runtime.last_scan_error)
        } else {
          ElMessage.success('归档扫描已完成')
        }
      }
    } catch {
      stopScanPolling()
    }
  }, 3000)
}

const retryTask = async (row) => {
  await archiveApi.retryTask(row.id)
  ElMessage.success('归档任务已重新执行')
  await loadTasks()
}

const clearFinished = async (includeFailed) => {
  try {
    await ElMessageBox.confirm(includeFailed ? '确认清理已完成和失败的归档任务吗？' : '确认清理已完成的归档任务吗？', '提示', { type: 'warning' })
    const { data } = await archiveApi.clearTasks(includeFailed)
    ElMessage.success(`已清理 ${data.removed || 0} 条任务记录`)
    await loadTasks()
  } catch (error) {
    if (error !== 'cancel') { /* cancelled */ }
  }
}

const handlePageChange = (page) => { filters.page = page; loadTasks() }
const handleFilterChange = () => { filters.page = 1; loadTasks() }

const openPicker = (target) => {
  pickerTarget.value = target
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
  // 如果点击的是当前目录，不做任何事
  if (cid === pickerCurrentCid.value) return
  
  // 查找目标目录在面包屑中的索引
  const index = pickerHistory.value.findIndex(h => h.cid === cid)
  if (index >= 0) {
    // 点击的是面包屑中的某个目录，截断历史
    pickerHistory.value = pickerHistory.value.slice(0, index)
  }
  // 否则是点击面包屑的根目录，清空历史
  else if (cid === '0') {
    pickerHistory.value = []
  }
  
  loadPickerFolders(cid)
}

const handlePickerRowClick = (row) => {
  enterPickerFolder(row)
}

const enterPickerFolder = (row) => {
  const rowName = getFolderDisplayName(row)
  // 进入子目录前，将当前目录加入历史
  const currentName = getCurrentFolderName()
  if (pickerCurrentCid.value !== '0' && !pickerHistory.value.find(h => h.cid === pickerCurrentCid.value)) {
    pickerHistory.value.push({ cid: pickerCurrentCid.value, name: currentName })
  }
  // 将目标目录加入历史（使用 row.name）
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
    if (!folderName) {
      return
    }

    pickerCreating.value = true
    await pan115Api.createFolder(pickerCurrentCid.value, folderName)
    ElMessage.success(`已创建文件夹：${folderName}`)
    await loadPickerFolders(pickerCurrentCid.value)
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
  } finally {
    pickerCreating.value = false
  }
}

const confirmPicker = () => {
  const folderName = getCurrentFolderName()
  if (pickerTarget.value === 'watch') {
    config.archive_watch_cid = pickerCurrentCid.value
    config.archive_watch_name = folderName
  } else {
    config.archive_output_cid = pickerCurrentCid.value
    config.archive_output_name = folderName
  }
  pickerVisible.value = false
  ElMessage.success('目录已选择，点击保存配置生效')
}

onMounted(async () => {
  await refreshAll()
  if (runtime.scan_running) {
    startScanPolling()
  }
})

onBeforeUnmount(() => {
  stopScanPolling()
})
</script>

<style lang="scss" scoped>
.archive-page {
  display: flex;
  flex-direction: column;
  gap: 16px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .page-subtitle {
    margin: 8px 0 0;
    color: var(--ms-text-secondary);
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }

  .card-title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .section-card .card-title {
    font-weight: 600;
    color: var(--ms-text-primary);
  }

  .config-form {
    .config-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 20px;
    }
    .grid-span-2 { grid-column: span 2; }
    .suffix-text { margin-left: 10px; color: var(--ms-text-secondary); }
    .config-actions { margin-top: 12px; }
  }

  .folder-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .form-hint {
    margin-top: 4px;
    font-size: 12px;
    color: var(--ms-text-secondary);
  }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 20px;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .status-item-full {
    grid-column: 1 / -1;
    align-items: flex-start;
  }

  .status-label {
    color: var(--ms-text-secondary);
    white-space: nowrap;
  }

  .status-value, .year-text, .muted-text {
    color: var(--ms-text-secondary);
  }

  .status-value {
    word-break: break-word;
  }

  .status-error {
    color: var(--el-color-danger);
  }

  .tasks-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }

  .tasks-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  .rules-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 12px;
  }

  .rules-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .rule-row {
    display: grid;
    grid-template-columns: 54px minmax(120px, 180px) 130px minmax(220px, 1fr) 64px;
    gap: 10px;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .drag-handle {
    cursor: move;
    color: var(--ms-text-secondary);
    font-size: 12px;
    user-select: none;
  }

  .rule-values {
    min-width: 0;
  }

  .status-filter { width: 140px; }
  .table-wrap { overflow-x: auto; }

  .pager-wrap {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }
}

.picker-breadcrumb { margin-bottom: 12px; }

.picker-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.picker-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  font-size: 13px;
  color: var(--ms-text-secondary);
}

@media (max-width: 1024px) {
  .archive-page {
    .page-header, .tasks-header { flex-direction: column; align-items: stretch; }
    .header-actions, .tasks-toolbar { width: 100%; }
    .config-form .config-grid, .status-grid { grid-template-columns: 1fr; }
    .config-form .grid-span-2 { grid-column: span 1; }
    .rule-row { grid-template-columns: 1fr; }
    .table-wrap .el-table { min-width: 980px; }
  }
}

@media (max-width: 768px) {
  .archive-page .header-actions { flex-direction: column; }
}
</style>

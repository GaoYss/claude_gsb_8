<template>
  <el-drawer :model-value="visible" size="720px"
             :title="detail.occupation_no ? `占绿审批 · ${detail.occupation_no}` : '占绿审批详情'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <el-alert v-if="detail.is_active" type="warning" :closable="false" show-icon
                title="该绿地处于占绿状态，占绿期间不参与养护考核"
                :description="`占绿中 / 待核验期间养护逾期、临期提醒与考核排名均对该绿地豁免，核验通过后自动恢复。`" />

      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="审批状态" :span="2">
          <EnumTag group="occupation_status" :value="detail.status" :label="detail.status_label" />
          <el-tag v-if="detail.is_active" type="warning" size="small" effect="plain" class="ml8">占绿生效中</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="所属绿地" :span="2">
          {{ detail.green_space ? `${detail.green_space.code} ${detail.green_space.name}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="占用事由">
          <EnumTag group="occupation_reason" :value="detail.reason" :label="detail.reason_label" />
        </el-descriptions-item>
        <el-descriptions-item label="占用面积">{{ formatArea(detail.occupy_area_sqm) }}</el-descriptions-item>
        <el-descriptions-item label="事由说明" :span="2">{{ detail.purpose }}</el-descriptions-item>
        <el-descriptions-item label="占用范围" :span="2">{{ detail.scope_description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请日期">{{ formatDate(detail.apply_date) }}</el-descriptions-item>
        <el-descriptions-item label="占用期限">
          {{ formatDate(detail.start_date) }} 至 {{ formatDate(detail.end_date) }}
        </el-descriptions-item>
        <el-descriptions-item label="申请单位/人">{{ detail.applicant || '-' }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detail.applicant_phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="恢复要求" :span="2">{{ detail.restore_requirement || '-' }}</el-descriptions-item>
      </el-descriptions>

      <!-- 审批信息 -->
      <div v-if="detail.approved_at || detail.status === 'pending'" class="section">
        <div class="section-title">审批信息</div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="审批人">{{ detail.approved_by || '待审批' }}</el-descriptions-item>
          <el-descriptions-item label="审批时间">{{ formatDateTime(detail.approved_at) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="审批意见" :span="2">{{ detail.approval_remark || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 恢复报备 -->
      <div v-if="['restored', 'verified'].includes(detail.status)" class="section">
        <div class="section-title">恢复报备与核验</div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="恢复完成日期">{{ formatDate(detail.restored_date) }}</el-descriptions-item>
          <el-descriptions-item label="实际恢复面积">
            <span :class="areaShort ? 'danger-text' : ''">{{ formatArea(detail.restored_area_sqm) }}</span>
            <span v-if="areaShort" class="danger-text">（少于审批面积）</span>
          </el-descriptions-item>
          <el-descriptions-item label="苗木恢复情况" :span="2">{{ detail.restored_plants || '-' }}</el-descriptions-item>
          <el-descriptions-item label="恢复说明" :span="2">{{ detail.restore_remark || '-' }}</el-descriptions-item>
          <el-descriptions-item label="核验人">{{ detail.verified_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="核验时间">{{ formatDateTime(detail.verified_at) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="核验意见" :span="2">{{ detail.verify_remark || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>

      <template v-if="detail.status === 'pending'">
        <el-button type="danger" plain :loading="acting" @click="act('rejected')">驳回</el-button>
        <el-button type="primary" :loading="acting" @click="act('approved')">审批通过</el-button>
      </template>
      <el-button v-if="detail.status === 'approved'" type="warning" :loading="acting" @click="openRestore">
        报备恢复完成
      </el-button>
      <el-button v-if="detail.status === 'restored'" type="primary" :loading="acting" @click="openVerify">
        恢复核验
      </el-button>
    </template>

    <!-- 审批弹窗 -->
    <el-dialog v-model="approvalVisible" :title="approvalAction === 'approved' ? '占绿审批 · 通过' : '占绿审批 · 驳回'"
               width="480px" append-to-body destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="审批人" required>
          <el-input v-model="approvalForm.approved_by" placeholder="审批人姓名" maxlength="64" />
        </el-form-item>
        <el-form-item label="审批意见">
          <el-input v-model="approvalForm.approval_remark" type="textarea" :rows="3" maxlength="2000"
                    :placeholder="approvalAction === 'approved' ? '同意占用，到期前完成恢复并申请核验' : '请填写驳回原因'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approvalVisible = false">取消</el-button>
        <el-button :type="approvalAction === 'approved' ? 'primary' : 'danger'"
                   @click="submitApproval">确认</el-button>
      </template>
    </el-dialog>

    <!-- 恢复报备弹窗 -->
    <el-dialog v-model="restoreVisible" title="恢复完成报备" width="520px" append-to-body destroy-on-close>
      <el-form :model="restoreForm" label-width="110px">
        <el-form-item label="恢复完成日期" required>
          <el-date-picker v-model="restoreForm.restored_date" type="date" value-format="YYYY-MM-DD"
                          style="width: 100%" />
        </el-form-item>
        <el-form-item label="实际恢复面积" required>
          <el-input-number v-model="restoreForm.restored_area_sqm" :min="0.01" :precision="2"
                           :controls="false" style="width: 100%" />
          <div class="form-hint">审批占用面积 {{ formatArea(detail.occupy_area_sqm) }}，少于该面积将无法通过核验</div>
        </el-form-item>
        <el-form-item label="苗木恢复情况" required>
          <el-input v-model="restoreForm.restored_plants" type="textarea" :rows="3" maxlength="2000"
                    placeholder="如：恢复香樟 6 株、草坪 260 平方米，规格与占用前一致" />
        </el-form-item>
        <el-form-item label="恢复说明">
          <el-input v-model="restoreForm.restore_remark" type="textarea" :rows="2" maxlength="2000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="restoreVisible = false">取消</el-button>
        <el-button type="warning" @click="submitRestore">提交报备</el-button>
      </template>
    </el-dialog>

    <!-- 核验弹窗 -->
    <el-dialog v-model="verifyVisible" title="恢复核验" width="480px" append-to-body destroy-on-close>
      <el-alert type="info" :closable="false" show-icon
                :title="`核对恢复面积（${formatArea(detail.restored_area_sqm)}）与苗木恢复情况`"
                description="恢复面积不得少于审批占用面积，苗木恢复情况须已登记。" class="mb12" />
      <el-form label-width="80px">
        <el-form-item label="核验人" required>
          <el-input v-model="verifyForm.verified_by" placeholder="核验人姓名" maxlength="64" />
        </el-form-item>
        <el-form-item label="核验意见">
          <el-input v-model="verifyForm.verify_remark" type="textarea" :rows="3" maxlength="2000"
                    placeholder="恢复面积与苗木规格符合审批要求，核验通过" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="verifyVisible = false">取消</el-button>
        <el-button type="primary" @click="submitVerify">核验通过</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { occupationApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import { formatArea, formatDate, formatDateTime, today } from '@/utils/format'

const emit = defineEmits(['updated'])

const visible = ref(false)
const loading = ref(false)
const acting = ref(false)
const currentId = ref(null)
const detail = ref({})

const approvalVisible = ref(false)
const approvalAction = ref('approved')
const approvalForm = reactive({ approved_by: '', approval_remark: '' })

const restoreVisible = ref(false)
const restoreForm = reactive(emptyRestore())

const verifyVisible = ref(false)
const verifyForm = reactive({ verified_by: '', verify_remark: '' })

function emptyRestore() {
  return { restored_date: today(), restored_area_sqm: null, restored_plants: '', restore_remark: '' }
}

const areaShort = computed(
  () => Number(detail.value.restored_area_sqm || 0) < Number(detail.value.occupy_area_sqm || 0),
)

async function open(id) {
  currentId.value = id
  visible.value = true
  await load()
}

async function load() {
  if (!currentId.value) return
  loading.value = true
  try {
    detail.value = await occupationApi.detail(currentId.value)
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
}

function act(action) {
  approvalAction.value = action
  approvalForm.approved_by = ''
  approvalForm.approval_remark = ''
  approvalVisible.value = true
}

async function submitApproval() {
  if (!approvalForm.approved_by.trim()) {
    ElMessage.warning('请填写审批人')
    return
  }
  acting.value = true
  try {
    await occupationApi.approve(currentId.value, { ...approvalForm, action: approvalAction.value })
    ElMessage.success(approvalAction.value === 'approved'
      ? '审批已通过，绿地已标记为占绿状态' : '占绿申请已驳回')
    approvalVisible.value = false
    await load()
    emit('updated')
  } finally {
    acting.value = false
  }
}

function openRestore() {
  Object.assign(restoreForm, emptyRestore())
  restoreForm.restored_area_sqm = detail.value.occupy_area_sqm
  restoreVisible.value = true
}

async function submitRestore() {
  if (!restoreForm.restored_date || !restoreForm.restored_area_sqm || !restoreForm.restored_plants.trim()) {
    ElMessage.warning('请完整填写恢复日期、面积与苗木恢复情况')
    return
  }
  acting.value = true
  try {
    await occupationApi.reportRestore(currentId.value, { ...restoreForm })
    ElMessage.success('恢复完成已报备，等待恢复核验')
    restoreVisible.value = false
    await load()
    emit('updated')
  } finally {
    acting.value = false
  }
}

async function openVerify() {
  verifyForm.verified_by = ''
  verifyForm.verify_remark = ''
  verifyVisible.value = true
}

async function submitVerify() {
  if (!verifyForm.verified_by.trim()) {
    ElMessage.warning('请填写核验人')
    return
  }
  acting.value = true
  try {
    await occupationApi.verify(currentId.value, { ...verifyForm })
    ElMessage.success('恢复核验通过，绿地已解除占绿状态并恢复养护考核')
    verifyVisible.value = false
    await load()
    emit('updated')
  } finally {
    acting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-weight: 600;
}

.ml8 {
  margin-left: 8px;
}

.mb12 {
  margin-bottom: 12px;
}

.danger-text {
  color: #f56c6c;
  font-weight: 600;
}
</style>

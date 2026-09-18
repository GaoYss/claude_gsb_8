<template>
  <el-drawer :model-value="visible" size="620px"
             :title="detail.occupation_no ? `占用登记 · ${detail.occupation_no}` : '占用登记详情'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <el-alert v-if="detail.status === 'approved'" type="warning" :closable="false" show-icon
                class="status-alert"
                :title="detail.is_expired ? '该占用已超期，请督促申请单位尽快恢复并核验' : '占绿中：占绿期间该绿地不参与养护考核'" />
      <el-alert v-else-if="detail.status === 'pending'" type="info" :closable="false" show-icon
                class="status-alert" title="待审批：审批通过后绿地将标记为占绿状态" />

      <div class="section-title">登记信息</div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="占用绿地" :span="2">
          {{ detail.green_space ? `${detail.green_space.code} ${detail.green_space.name}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="申请单位/人">{{ detail.applicant || '-' }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detail.contact_phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="占用类型">
          <EnumTag group="occupation_category" :value="detail.category" :label="detail.category_label" />
        </el-descriptions-item>
        <el-descriptions-item label="占用面积">{{ formatNumber(detail.area_sqm) }} ㎡</el-descriptions-item>
        <el-descriptions-item label="占用开始">{{ formatDate(detail.start_date) }}</el-descriptions-item>
        <el-descriptions-item label="计划恢复">
          {{ formatDate(detail.end_date) }}
          <el-tag v-if="detail.is_expired" type="danger" size="small" effect="plain">超期</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="占用事由" :span="2">{{ detail.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="占用范围" :span="2">{{ detail.location_desc || '-' }}</el-descriptions-item>
        <el-descriptions-item label="恢复要求" :span="2">{{ detail.restoration_requirement || '-' }}</el-descriptions-item>
        <el-descriptions-item label="占用状态">
          <EnumTag group="occupation_status" :value="detail.status" :label="detail.status_label" />
        </el-descriptions-item>
        <el-descriptions-item label="登记人">{{ detail.operator || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <template v-if="detail.status !== 'pending'">
        <div class="section-title">审批信息</div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="审批人">{{ detail.approved_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="审批时间">{{ formatDateTime(detail.approved_at) }}</el-descriptions-item>
          <el-descriptions-item label="审批意见" :span="2">{{ detail.approval_comment || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>

      <template v-if="detail.verify_result">
        <div class="section-title">恢复核验</div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="核验结论">
            <EnumTag group="verify_result" :value="detail.verify_result" :label="detail.verify_result_label" />
          </el-descriptions-item>
          <el-descriptions-item label="恢复面积">{{ formatNumber(detail.restored_area_sqm) }} ㎡</el-descriptions-item>
          <el-descriptions-item label="核验人">{{ detail.verified_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="核验时间">{{ formatDateTime(detail.verified_at) }}</el-descriptions-item>
          <el-descriptions-item label="苗木恢复情况" :span="2">{{ detail.plant_restoration || '-' }}</el-descriptions-item>
          <el-descriptions-item label="核验意见" :span="2">{{ detail.verify_comment || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref } from 'vue'

import { greenOccupationApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import { formatDate, formatDateTime, formatNumber } from '@/utils/format'

const visible = ref(false)
const loading = ref(false)
const detail = ref({})

async function open(id) {
  visible.value = true
  loading.value = true
  try {
    detail.value = await greenOccupationApi.detail(id)
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.status-alert {
  margin-bottom: 14px;
}

.section-title {
  font-weight: 600;
  margin: 14px 0 8px;
}
</style>

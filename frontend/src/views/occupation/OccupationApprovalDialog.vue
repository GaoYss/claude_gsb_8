<template>
  <el-dialog :model-value="visible" title="占用审批" width="560px" top="8vh"
             destroy-on-close @update:model-value="close">
    <div v-if="occupation" class="occ-summary">
      <div class="occ-summary__title">{{ occupation.reason }}</div>
      <div class="occ-summary__meta">
        {{ occupation.green_space?.name }} · {{ formatNumber(occupation.area_sqm) }} ㎡ ·
        {{ occupation.start_date }} ~ {{ occupation.end_date }}
      </div>
      <div class="occ-summary__meta">申请单位/人：{{ occupation.applicant }}</div>
    </div>

    <el-alert v-if="form.result === 'approved'" type="warning" :closable="false" show-icon
              title="批准后该绿地将标记为「占绿中」，占绿期间不参与养护考核" class="approve-alert" />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="审批结论" prop="result" :error="fieldErrors.result">
        <el-radio-group v-model="form.result">
          <el-radio-button v-for="item in resultOptions" :key="item.value"
                           :value="item.value">{{ item.label }}</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="审批人" prop="approved_by" :error="fieldErrors.approved_by">
        <el-input v-model="form.approved_by" placeholder="审批单位或审批人" maxlength="64" />
      </el-form-item>
      <el-form-item label="审批意见" :error="fieldErrors.approval_comment">
        <el-input v-model="form.approval_comment" type="textarea" :rows="3" maxlength="500"
                  :placeholder="form.result === 'rejected' ? '请说明驳回原因' : '可填写恢复要求补充、注意事项等'" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button :type="form.result === 'approved' ? 'primary' : 'danger'"
                 :loading="submitting" @click="submit">
        {{ form.result === 'approved' ? '批准占用' : '驳回申请' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { greenOccupationApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { formatNumber } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: resultOptions } = useEnumOptions('approval_result')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const occupation = ref(null)
const fieldErrors = ref({})
const form = reactive({ result: 'approved', approved_by: '', approval_comment: '' })

const rules = {
  result: [{ required: true, message: '请选择审批结论', trigger: 'change' }],
  approved_by: [{ required: true, message: '请填写审批人', trigger: 'blur' }],
}

function open(row) {
  occupation.value = row
  Object.assign(form, { result: 'approved', approved_by: '', approval_comment: '' })
  fieldErrors.value = {}
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  try {
    await greenOccupationApi.approve(occupation.value.id, { ...form })
    ElMessage.success(form.result === 'approved' ? '占用申请已批准，绿地已标记为占绿状态' : '占用申请已驳回')
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.occ-summary {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: var(--gs-bg);
  border-radius: 6px;
}

.occ-summary__title {
  font-weight: 600;
  margin-bottom: 4px;
}

.occ-summary__meta {
  color: #909399;
  font-size: 13px;
  line-height: 1.7;
}

.approve-alert {
  margin-bottom: 16px;
}
</style>

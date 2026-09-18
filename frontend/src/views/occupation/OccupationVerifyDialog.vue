<template>
  <el-dialog :model-value="visible" title="恢复核验" width="600px" top="6vh"
             destroy-on-close @update:model-value="close">
    <div v-if="occupation" class="occ-summary">
      <div class="occ-summary__title">{{ occupation.reason }}</div>
      <div class="occ-summary__meta">
        {{ occupation.green_space?.name }} · 占用 {{ formatNumber(occupation.area_sqm) }} ㎡ ·
        {{ occupation.start_date }} ~ {{ occupation.end_date }}
        <el-tag v-if="occupation.is_expired" type="danger" size="small" effect="plain">已超期</el-tag>
      </div>
      <div class="occ-summary__require">恢复要求：{{ occupation.restoration_requirement || '-' }}</div>
    </div>

    <el-alert v-if="occupation?.verify_result === 'unqualified'" type="error" :closable="false" show-icon
              class="verify-alert" title="上次核验不合格，本次为整改后复检"
              :description="`核验人 ${occupation.verified_by || '-'}（${formatDateTime(occupation.verified_at)}）：${occupation.verify_comment || '无核验意见'}`" />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="核验结论" prop="verify_result" :error="fieldErrors.verify_result">
        <el-radio-group v-model="form.verify_result">
          <el-radio-button v-for="item in resultOptions" :key="item.value"
                           :value="item.value">{{ item.label }}</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="恢复面积（㎡）" prop="restored_area_sqm" :error="fieldErrors.restored_area_sqm">
        <el-input-number v-model="form.restored_area_sqm" :min="0" :max="99999999" :precision="2"
                         :controls="false" placeholder="实际恢复的绿化面积" style="width: 100%" />
      </el-form-item>
      <el-form-item label="苗木恢复情况" prop="plant_restoration" :error="fieldErrors.plant_restoration">
        <el-input v-model="form.plant_restoration" type="textarea" :rows="3" maxlength="2000"
                  placeholder="补植苗木品种、数量、规格与长势情况" />
      </el-form-item>
      <el-form-item label="核验人" prop="verified_by" :error="fieldErrors.verified_by">
        <el-input v-model="form.verified_by" maxlength="64" />
      </el-form-item>
      <el-form-item label="核验意见" :error="fieldErrors.verify_comment">
        <el-input v-model="form.verify_comment" type="textarea" :rows="2" maxlength="500"
                  :placeholder="form.verify_result === 'unqualified' ? '请说明需整改的内容' : '可填写核验说明'" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button :type="form.verify_result === 'qualified' ? 'success' : 'danger'"
                 :loading="submitting" @click="submit">
        提交核验结论
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { greenOccupationApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { formatDateTime, formatNumber } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: resultOptions } = useEnumOptions('verify_result')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const occupation = ref(null)
const fieldErrors = ref({})
const form = reactive({
  verify_result: 'qualified',
  restored_area_sqm: null,
  plant_restoration: '',
  verified_by: '',
  verify_comment: '',
})

const rules = {
  verify_result: [{ required: true, message: '请选择核验结论', trigger: 'change' }],
  restored_area_sqm: [{ required: true, message: '请填写恢复面积', trigger: 'blur' }],
  plant_restoration: [{ required: true, message: '请填写苗木恢复情况', trigger: 'blur' }],
  verified_by: [{ required: true, message: '请填写核验人', trigger: 'blur' }],
}

function open(row) {
  occupation.value = row
  Object.assign(form, {
    verify_result: 'qualified',
    restored_area_sqm: row.area_sqm ?? null,
    plant_restoration: '',
    verified_by: '',
    verify_comment: '',
  })
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
    await greenOccupationApi.verify(occupation.value.id, { ...form })
    ElMessage.success(
      form.verify_result === 'qualified' ? '恢复核验合格，绿地已恢复正常养护' : '恢复核验不合格，请整改后重新核验',
    )
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

.occ-summary__require {
  margin-top: 6px;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
}

.verify-alert {
  margin-bottom: 16px;
}
</style>

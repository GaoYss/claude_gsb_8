<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑占绿申请 · ${form.occupation_no || ''}` : '占绿申请登记'"
             width="780px" top="5vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" :disabled="isEdit" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="占用事由" prop="reason" :error="fieldErrors.reason">
            <el-select v-model="form.reason" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in reasonOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="占用面积(㎡)" prop="occupy_area_sqm" :error="fieldErrors.occupy_area_sqm">
            <el-input-number v-model="form.occupy_area_sqm" :min="0.01" :max="99999999" :precision="2"
                             :controls="false" placeholder="实际占用面积" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="事由说明" prop="purpose" :error="fieldErrors.purpose">
            <el-input v-model="form.purpose" placeholder="如：地铁出入口配套施工临时占用绿地" maxlength="255" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="占用范围" :error="fieldErrors.scope_description">
            <el-input v-model="form.scope_description" type="textarea" :rows="2" maxlength="2000"
                      placeholder="描述占用的具体位置、边界、围挡方式等" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="申请日期" prop="apply_date" :error="fieldErrors.apply_date">
            <el-date-picker v-model="form.apply_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="占用开始" prop="start_date" :error="fieldErrors.start_date">
            <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="开始日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="占用结束" prop="end_date" :error="fieldErrors.end_date">
            <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="结束日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="申请单位/人" :error="fieldErrors.applicant">
            <el-input v-model="form.applicant" placeholder="占用申请单位或申请人" maxlength="96" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="联系电话" :error="fieldErrors.applicant_phone">
            <el-input v-model="form.applicant_phone" maxlength="32" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="恢复要求" :error="fieldErrors.restore_requirement">
            <el-input v-model="form.restore_requirement" type="textarea" :rows="3" maxlength="2000"
                      placeholder="占用期满后绿地与苗木的恢复标准、期限与责任要求" />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { occupationApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: reasonOptions } = useEnumOptions('occupation_reason')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const editingStatus = ref('pending')
const fieldErrors = ref({})
const spacePreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  green_space_id: [{ required: true, message: '请选择所属绿地', trigger: 'change' }],
  reason: [{ required: true, message: '请选择占用事由', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写事由说明', trigger: 'blur' }],
  occupy_area_sqm: [{ required: true, message: '请填写占用面积', trigger: 'blur' }],
  apply_date: [{ required: true, message: '请选择申请日期', trigger: 'change' }],
  start_date: [{ required: true, message: '请选择占用开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择占用结束日期', trigger: 'change' }],
}

function emptyForm() {
  return {
    occupation_no: '',
    green_space_id: null,
    reason: 'construction',
    purpose: '',
    scope_description: '',
    occupy_area_sqm: null,
    apply_date: today(),
    start_date: '',
    end_date: '',
    applicant: '',
    applicant_phone: '',
    restore_requirement: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  editingId.value = row?.id ?? null
  editingStatus.value = row?.status ?? 'pending'
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
  }
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
  const payload = { ...form }
  if (!payload.occupation_no) delete payload.occupation_no
  try {
    if (isEdit.value) {
      await occupationApi.update(editingId.value, payload)
      ElMessage.success('占绿申请已更新')
    } else {
      await occupationApi.create(payload)
      ElMessage.success('占绿申请登记成功，等待审批')
    }
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

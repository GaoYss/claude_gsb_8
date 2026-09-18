<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑占用登记 · ${form.occupation_no}` : '登记占用申请'"
             width="720px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="占用绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="申请单位/人" prop="applicant" :error="fieldErrors.applicant">
            <el-input v-model="form.applicant" placeholder="如：某建设工程公司" maxlength="96" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="联系电话" :error="fieldErrors.contact_phone">
            <el-input v-model="form.contact_phone" maxlength="32" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="占用类型" prop="category" :error="fieldErrors.category">
            <el-select v-model="form.category" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="占用面积（㎡）" prop="area_sqm" :error="fieldErrors.area_sqm">
            <el-input-number v-model="form.area_sqm" :min="0.01" :max="99999999" :precision="2"
                             :controls="false" placeholder="不得超过绿地总面积" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="占用开始日期" prop="start_date" :error="fieldErrors.start_date">
            <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计划恢复日期" prop="end_date" :error="fieldErrors.end_date">
            <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="占用事由" prop="reason" :error="fieldErrors.reason">
        <el-input v-model="form.reason" placeholder="如：地铁施工临时占用绿化带" maxlength="255" />
      </el-form-item>
      <el-form-item label="占用范围说明" :error="fieldErrors.location_desc">
        <el-input v-model="form.location_desc" placeholder="如：××路交叉口东南侧绿化带" maxlength="255" />
      </el-form-item>
      <el-form-item label="恢复要求" prop="restoration_requirement" :error="fieldErrors.restoration_requirement">
        <el-input v-model="form.restoration_requirement" type="textarea" :rows="3" maxlength="2000"
                  placeholder="恢复期限、恢复面积、苗木品种与成活率等要求，作为恢复核验依据" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="登记人" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
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

import { greenOccupationApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: categoryOptions } = useEnumOptions('occupation_category')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  green_space_id: [{ required: true, message: '请选择占用绿地', trigger: 'change' }],
  applicant: [{ required: true, message: '请输入申请单位/人', trigger: 'blur' }],
  category: [{ required: true, message: '请选择占用类型', trigger: 'change' }],
  reason: [{ required: true, message: '请输入占用事由', trigger: 'blur' }],
  area_sqm: [{ required: true, message: '请输入占用面积', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择占用开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择计划恢复日期', trigger: 'change' }],
  restoration_requirement: [{ required: true, message: '请填写恢复要求', trigger: 'blur' }],
}

function emptyForm() {
  return {
    occupation_no: '',
    green_space_id: null,
    applicant: '',
    contact_phone: '',
    category: 'construction',
    reason: '',
    location_desc: '',
    area_sqm: null,
    start_date: today(),
    end_date: '',
    restoration_requirement: '',
    operator: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  editingId.value = row?.id ?? null
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
      await greenOccupationApi.update(editingId.value, payload)
      ElMessage.success('绿地占用登记已更新')
    } else {
      await greenOccupationApi.create(payload)
      ElMessage.success('绿地占用登记成功，待审批')
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

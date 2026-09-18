<template>
  <div class="page">
    <PageHeader title="占绿审批与恢复核验" description="登记占用事由、范围、期限与恢复要求，审批后标记占绿，恢复完成核验面积与苗木">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记占绿申请</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 事由 / 申请单位 / 范围" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按绿地筛选" @update:model-value="search" />
        </div>
        <el-select v-model="filters.status" placeholder="审批状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.reason" placeholder="占用事由" clearable @change="search">
          <el-option v-for="item in reasonOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="占用开始起" end-placeholder="占用开始止" @change="onDateChange" />
        <el-checkbox v-model="filters.active_only" label="仅看占绿生效" border @change="search" />
        <el-checkbox v-model="filters.overdue_restore" label="到期未恢复" border @change="search" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="占绿申请" :value="formatNumber(summary?.total_count ?? 0)" unit="条"
                hint="全部审批记录" icon="Document" />
      <StatCard label="占绿生效中" :value="formatNumber(summary?.active_count ?? 0)" unit="处绿地"
                :hint="`占用面积合计 ${formatArea(summary?.active_area_sqm ?? 0)}`"
                tone="warning" icon="WarningFilled" />
      <StatCard label="到期未恢复" :value="formatNumber(summary?.overdue_restore_count ?? 0)" unit="条"
                hint="占用期限已满仍未报备恢复"
                :tone="summary?.overdue_restore_count ? 'danger' : 'default'" icon="AlarmClock" />
      <StatCard label="待核验 / 核验通过"
                :value="`${formatNumber(summary?.by_status?.restored?.count ?? 0)} / ${formatNumber(summary?.by_status?.verified?.count ?? 0)}`"
                :hint="`驳回 ${formatNumber(summary?.by_status?.rejected?.count ?? 0)} 条`"
                tone="info" icon="CircleCheck" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条占绿申请，
          占绿中 <strong>{{ summary?.by_status?.approved?.count ?? 0 }}</strong>、
          待核验 <strong>{{ summary?.by_status?.restored?.count ?? 0 }}</strong>、
          核验通过 <strong>{{ summary?.by_status?.verified?.count ?? 0 }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>占用范围：</b>{{ row.scope_description || '-' }}</span>
              <span><b>申请日期：</b>{{ formatDate(row.apply_date) }}</span>
              <span><b>申请单位/人：</b>{{ row.applicant || '-' }}</span>
              <span><b>联系电话：</b>{{ row.applicant_phone || '-' }}</span>
              <span><b>审批人：</b>{{ row.approved_by || '-' }}</span>
              <span><b>审批时间：</b>{{ formatDateTime(row.approved_at) || '-' }}</span>
              <span v-if="row.restored_date"><b>恢复完成：</b>{{ formatDate(row.restored_date) }}，
                实际恢复 {{ formatArea(row.restored_area_sqm) }}</span>
              <span v-if="row.verified_by"><b>核验人：</b>{{ row.verified_by }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="occupation_no" label="编号" width="150" />
        <el-table-column label="所属绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.green_space?.name || '-' }}</div>
            <el-tag v-if="row.is_active" type="warning" size="small" effect="plain">占绿中</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="占用事由" width="130">
          <template #default="{ row }">
            <EnumTag group="occupation_reason" :value="row.reason" :label="row.reason_label" />
          </template>
        </el-table-column>
        <el-table-column prop="purpose" label="事由说明" min-width="180" show-overflow-tooltip />
        <el-table-column label="占用面积" width="105" align="right">
          <template #default="{ row }">{{ formatArea(row.occupy_area_sqm) }}</template>
        </el-table-column>
        <el-table-column label="占用期限" width="180">
          <template #default="{ row }">
            <div>{{ formatDate(row.start_date) }}</div>
            <div class="cell-sub">至 {{ formatDate(row.end_date) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <EnumTag group="occupation_status" :value="row.status" :label="row.status_label" />
            <el-tag v-if="row.status === 'approved' && isOverdue(row)" type="danger" size="small" effect="plain">
              到期未恢复
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="drawer.open(row.id)">详情/办理</el-button>
            <el-button v-if="row.status === 'pending'" link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button v-if="['pending', 'rejected'].includes(row.status)"
                       link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <OccupationFormDialog ref="formDialog" @saved="load" />
    <OccupationDetailDrawer ref="drawer" @updated="load" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { occupationApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatArea, formatDate, formatDateTime, formatNumber, today } from '@/utils/format'

import OccupationDetailDrawer from './OccupationDetailDrawer.vue'
import OccupationFormDialog from './OccupationFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const drawer = ref(null)
const dateRange = ref([])

const { options: statusOptions } = useEnumOptions('occupation_status')
const { options: reasonOptions } = useEnumOptions('occupation_reason')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(occupationApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      status: '',
      reason: '',
      date_from: '',
      date_to: '',
      active_only: false,
      overdue_restore: false,
    },
  })

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function reset() {
  dateRange.value = []
  resetFilters()
}

function isOverdue(row) {
  return row.status === 'approved' && row.end_date < today()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除占绿申请「${row.occupation_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await occupationApi.remove(row.id)
    ElMessage.success('占绿申请已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}
</style>

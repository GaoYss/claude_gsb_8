<template>
  <div class="page">
    <PageHeader title="占绿管理" description="占用绿地登记、审批、占绿状态标记与恢复核验全过程管理">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记占用申请</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 申请单位 / 占用事由" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按绿地筛选" @update:model-value="search" />
        </div>
        <el-select v-model="filters.status" placeholder="占用状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.category" placeholder="占用类型" clearable @change="search">
          <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="占用开始起" end-placeholder="占用开始止" @change="onDateChange" />
        <el-checkbox v-model="filters.expired" label="仅看超期" border @change="search" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="待审批" :value="formatNumber(summary?.by_status?.pending ?? 0)" unit="条"
                hint="登记后等待审批的占用申请" icon="Timer" />
      <StatCard label="占绿中" :value="formatNumber(summary?.by_status?.approved ?? 0)" unit="条"
                :hint="`占用面积合计 ${formatArea(summary?.occupied_area ?? 0)}`" tone="warning" icon="OfficeBuilding" />
      <StatCard label="超期未恢复" :value="formatNumber(summary?.expired_count ?? 0)" unit="条"
                :hint="`另有 ${formatNumber(summary?.expiring_soon_count ?? 0)} 条 ${EXPIRING_SOON_DAYS} 天内到期`"
                :tone="summary?.expired_count ? 'danger' : 'default'" icon="Warning" />
      <StatCard label="已恢复" :value="formatNumber(summary?.by_status?.completed ?? 0)" unit="条"
                hint="恢复核验合格，绿地已恢复养护" tone="success" icon="CircleCheck" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条占用登记，
          占绿中 <strong>{{ summary?.by_status?.approved ?? 0 }}</strong> 条，
          占用面积 <strong>{{ formatArea(summary?.occupied_area ?? 0) }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="占用编号 / 事由" min-width="230" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-main">{{ row.reason }}</div>
            <div class="cell-sub">{{ row.occupation_no }}</div>
          </template>
        </el-table-column>
        <el-table-column label="占用绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="applicant" label="申请单位/人" min-width="150" show-overflow-tooltip />
        <el-table-column label="占用类型" width="105">
          <template #default="{ row }">
            <EnumTag group="occupation_category" :value="row.category" :label="row.category_label" />
          </template>
        </el-table-column>
        <el-table-column label="占用面积" width="105" align="right">
          <template #default="{ row }">{{ formatNumber(row.area_sqm) }} ㎡</template>
        </el-table-column>
        <el-table-column label="占用期限" width="200">
          <template #default="{ row }">
            <div>{{ row.start_date }} ~ {{ row.end_date }}</div>
            <el-tag v-if="row.is_expired" type="danger" size="small" effect="plain">超期未恢复</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92">
          <template #default="{ row }">
            <EnumTag group="occupation_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column label="最近核验" width="105">
          <template #default="{ row }">
            <EnumTag v-if="row.verify_result" group="verify_result" :value="row.verify_result"
                     :label="row.verify_result_label" />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="detailDrawer.open(row.id)">详情</el-button>
            <el-button v-if="row.status === 'pending'" link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button v-if="row.status === 'pending'" link type="warning" @click="approvalDialog.open(row)">审批</el-button>
            <el-button v-if="row.status === 'approved'" link type="success" @click="verifyDialog.open(row)">恢复核验</el-button>
            <el-button v-if="row.status !== 'approved'" link type="danger" @click="remove(row)">删除</el-button>
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
    <OccupationApprovalDialog ref="approvalDialog" @saved="load" />
    <OccupationVerifyDialog ref="verifyDialog" @saved="load" />
    <OccupationDetailDrawer ref="detailDrawer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { greenOccupationApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatArea, formatNumber } from '@/utils/format'

import OccupationApprovalDialog from './OccupationApprovalDialog.vue'
import OccupationDetailDrawer from './OccupationDetailDrawer.vue'
import OccupationFormDialog from './OccupationFormDialog.vue'
import OccupationVerifyDialog from './OccupationVerifyDialog.vue'

// 与后端 GreenOccupationService.EXPIRING_SOON_DAYS 保持一致
const EXPIRING_SOON_DAYS = 14

const route = useRoute()
const formDialog = ref(null)
const approvalDialog = ref(null)
const verifyDialog = ref(null)
const detailDrawer = ref(null)
const dateRange = ref([])

const { options: statusOptions } = useEnumOptions('occupation_status')
const { options: categoryOptions } = useEnumOptions('occupation_category')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(greenOccupationApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      status: '',
      category: '',
      date_from: '',
      date_to: '',
      expired: false,
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

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除占用登记「${row.occupation_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await greenOccupationApi.remove(row.id)
    ElMessage.success('绿地占用登记已删除')
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
</style>

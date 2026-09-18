import { createResourceApi } from './client'
import http from './client'

export const greenOccupationApi = {
  ...createResourceApi('green-occupations'),
  summary: (params) => http.get('/green-occupations/summary', { params }),
  /** 占用审批：{ result: 'approved' | 'rejected', approved_by, approval_comment } */
  approve: (id, payload) => http.patch(`/green-occupations/${id}/approval`, payload),
  /** 恢复核验：{ verify_result, restored_area_sqm, plant_restoration, verified_by, verify_comment } */
  verify: (id, payload) => http.patch(`/green-occupations/${id}/verification`, payload),
}

import { createResourceApi } from './client'
import http from './client'

export const occupationApi = {
  ...createResourceApi('occupations'),
  summary: (params) => http.get('/occupations/summary', { params }),
  approve: (id, payload) => http.patch(`/occupations/${id}/approval`, payload),
  reportRestore: (id, payload) => http.patch(`/occupations/${id}/restore`, payload),
  verify: (id, payload) => http.patch(`/occupations/${id}/verify`, payload),
}

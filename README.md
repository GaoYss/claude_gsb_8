# 城市绿地养护记录系统

面向城市绿化养护单位的一体化记录系统：以**绿地台账**为主线，串联**养护任务登记**、**养护记录录入**、**绿植更换记录**与**占绿审批及恢复核验**，并提供养护总览看板。

- 后端：Flask 3 + SQLAlchemy 2 + Flask-Migrate + Gunicorn（分层：api / schemas / services / models）
- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts（按业务模块拆分视图）
- 数据库：本地默认 SQLite，容器编排使用 PostgreSQL 16
- 部署：docker-compose 一键拉起 db / backend / frontend（nginx 托管静态资源并反向代理 /api）

## 一、功能模块

| 模块 | 页面 | 主要能力 |
| --- | --- | --- |
| 养护总览 | `/dashboard` | 绿地与养护总量指标、近半年记录与工时趋势、绿地类型/任务类型/更换原因分布、逾期任务提醒、养护工作量排名、占绿到期与待核验提醒 |
| 绿地台账 | `/green-spaces` | 绿地建档（编号自动生成）、按行政区/类型/等级/状态/关键字检索、占绿状态标记、档案详情（概览 + 近期任务/记录/更换/占绿 + 更换原因汇总）、删除保护 |
| 占绿审批 | `/occupations` | 占绿申请（编号按日生成）登记事由/范围/期限/恢复要求、审批通过/驳回、审批通过后在地块标记占绿、占绿期间绿地不参与养护考核、恢复完成报备、恢复面积与苗木恢复情况核验 |
| 养护任务 | `/tasks` | 任务登记（编号按日生成）、按状态/类型/优先级/绿地/计划日期区间/逾期筛选、状态流转（待执行→进行中→已完成/已取消）、任务详情与执行进度 |
| 养护记录 | `/records` | 记录录入（可关联任务，也可登记日常巡查）、工时/天气/材料/质量评定、质量分布与工时汇总、记录详情 |
| 绿植更换 | `/replacements` | 更换登记（植株、类别、规格、数量、原因、原植株状况、供苗单位、单价与金额）、按类别/原因统计与占比、按绿地/日期区间筛选 |

## 二、目录结构

```
.
├── backend/                     # Flask 后端
│   ├── app/
│   │   ├── __init__.py          # 应用工厂：装配扩展、蓝图、错误处理、CLI
│   │   ├── config.py            # 配置（SQLite / PostgreSQL 切换）
│   │   ├── constants.py         # 业务字典（唯一枚举来源，下发给前端）
│   │   ├── errors.py            # 业务异常与全局错误响应
│   │   ├── cli.py               # init-db / reset-db / seed 命令
│   │   ├── api/                 # 接口层：每个业务模块一个 Blueprint
│   │   │   ├── green_spaces.py
│   │   │   ├── occupations.py
│   │   │   ├── maintenance_tasks.py
│   │   │   ├── maintenance_records.py
│   │   │   ├── plant_replacements.py
│   │   │   ├── statistics.py
│   │   │   └── meta.py
│   │   ├── schemas/             # 校验层：写库字段校验 + 查询条件解析
│   │   │   ├── common.py        # 链式字段校验器（含跨字段 check）
│   │   │   ├── filters.py       # 列表过滤条件
│   │   │   └── green_space.py / occupation.py / maintenance_task.py / maintenance_record.py / plant_replacement.py
│   │   ├── services/            # 业务层：事务、编号生成、跨模块规则
│   │   │   ├── base_service.py  # 通用增删改与编号冲突重试
│   │   │   ├── code_generator.py
│   │   │   ├── green_space_service.py
│   │   │   ├── occupation_service.py
│   │   │   ├── maintenance_task_service.py
│   │   │   ├── maintenance_record_service.py
│   │   │   ├── plant_replacement_service.py
│   │   │   └── statistics_service.py
│   │   ├── models/              # 模型层：SQLAlchemy 模型与序列化
│   │   └── utils/               # 响应封装、分页、日期、排序等
│   ├── tests/                   # pytest 测试（接口 + 业务规则 + 端到端流程）
│   ├── docker/entrypoint.sh     # 等库就绪 → 建表 → 可选写入演示数据
│   ├── requirements.txt
│   └── wsgi.py                  # 入口（flask run / gunicorn 共用）
│
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # 按模块拆分的接口封装 + axios 拦截器
│   │   ├── components/common/   # PageHeader、StatCard、EnumTag、绿地/任务/记录选择器、图表容器
│   │   ├── composables/         # useListQuery（列表分页筛选）、useEnumOptions
│   │   ├── layouts/             # DefaultLayout（侧边导航 + 顶栏）
│   │   ├── router/              # 路由（按模块懒加载）
│   │   ├── stores/              # Pinia：字典缓存、布局状态
│   │   ├── styles/              # 全局样式与主题变量
│   │   ├── utils/               # 数值/面积/金额/日期格式化
│   │   └── views/               # 视图：dashboard / green-space / task / record / replacement
│   ├── docker/nginx.conf        # 静态资源 + /api 反向代理
│   ├── vite.config.js           # 开发代理 /api → 后端
│   └── package.json
│
├── docker-compose.yml           # db + backend + frontend 编排
├── .env.example
└── README.md
```

## 三、快速开始

### 方式一：docker-compose（推荐）

```bash
cp .env.example .env          # 可选：调整端口、数据库口令、是否写入演示数据
docker compose up -d --build
```

启动后访问：

- 前端：<http://localhost:8090>
- 后端接口：<http://localhost:5000/api/v1/meta/health>
- PostgreSQL：`localhost:5432`（容器内 `db:5432`）

首次启动会自动建表；`SEED_DEMO_DATA=true` 时会写入一批演示数据（7 处绿地、15 条任务、22 条养护记录、8 条更换记录、6 条占绿记录）。停止与清理：

```bash
docker compose down            # 停止容器，保留数据库卷
docker compose down -v         # 连同数据库卷一起清理
```

### 方式二：本地开发

后端（Python 3.11+，默认使用 SQLite，数据库文件位于 `backend/instance/green_space.db`）：

```bash
cd backend
pip install -r requirements.txt
flask --app wsgi seed --reset      # 建表 + 写入演示数据（可省略）
flask --app wsgi run --debug       # http://127.0.0.1:5000
```

前端（Node 18+）：

```bash
cd frontend
npm install
npm run dev                        # http://127.0.0.1:5173，/api 自动代理到 5000
```

生产构建与本地预览：

```bash
cd frontend && npm run build && npm run preview
```

## 四、环境变量

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | 数据库连接串，留空则使用 SQLite | 空（SQLite） |
| `AUTO_CREATE_TABLES` | 启动时自动建表 | `true` |
| `SEED_DEMO_DATA` | 容器启动时写入演示数据 | `false`（compose 中为 `true`） |
| `CORS_ORIGINS` | 允许的跨域来源 | `*` |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | 分页默认与上限 | `10` / `100` |
| `INSTANCE_DIR` | SQLite 数据文件目录 | `backend/instance` |
| `VITE_API_BASE_URL` | 前端接口前缀 | `/api/v1` |
| `VITE_PROXY_TARGET` | 开发代理目标 | `http://127.0.0.1:5000` |

## 五、接口一览（前缀 `/api/v1`）

统一响应结构：成功 `{"success": true, "code": 0, "message": "ok", "data": ...}`；失败 `{"success": false, "code": 4xxxx, "message": "...", "data": {"字段": "提示"}}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/meta/enums` | 全部业务字典（前端下拉唯一来源） |
| GET | `/meta/health` | 健康检查（含数据库连通性） |
| GET | `/green-spaces` | 台账列表（`keyword`/`district`/`green_type`/`maintenance_grade`/`status`/`sort`/`order`/分页，返回汇总） |
| GET | `/green-spaces/options` | 绿地下拉选项（排除已归档） |
| GET | `/green-spaces/districts` | 行政区及绿地处数 |
| POST | `/green-spaces` | 新增绿地（编号可留空自动生成） |
| GET | `/green-spaces/{id}` | 绿地详情 |
| GET | `/green-spaces/{id}/profile` | 绿地档案（概览统计 + 近期任务/记录/更换） |
| PUT | `/green-spaces/{id}` | 更新绿地（编号不可改） |
| DELETE | `/green-spaces/{id}?force=true` | 删除绿地（有关联数据时需 `force`） |
| GET/POST | `/maintenance-tasks` | 任务列表 / 登记任务（`status`/`task_type`/`priority`/`green_space_id`/`date_from`/`date_to`/`overdue`） |
| GET/PUT/DELETE | `/maintenance-tasks/{id}` | 任务详情（含执行进度与记录） / 更新 / 删除（有记录时需 `force`，记录会保留但解除关联） |
| PATCH | `/maintenance-tasks/{id}/status` | 任务状态流转 |
| GET/POST | `/maintenance-records` | 记录列表（`task_id`/`green_space_id`/`quality_result`/`weather`/`unlinked`/日期区间，返回汇总） / 录入记录 |
| GET/PUT/DELETE | `/maintenance-records/{id}` | 记录详情（含关联更换记录） / 更新 / 删除 |
| GET | `/maintenance-records/summary` | 记录汇总（条数、工时、质量分布） |
| GET/POST | `/plant-replacements` | 更换记录列表（`green_space_id`/`plant_category`/`reason`/日期区间，返回汇总） / 登记更换 |
| GET/PUT/DELETE | `/plant-replacements/{id}` | 详情 / 更新 / 删除 |
| GET | `/plant-replacements/summary` | 更换汇总（按植物类别、更换原因） |
| GET/POST | `/occupations` | 占绿列表（`green_space_id`/`status`/`reason`/`active_only`/`overdue_restore`/日期区间，返回汇总） / 登记占绿申请 |
| GET/PUT/DELETE | `/occupations/{id}` | 占绿详情 / 修改（仅待审批） / 删除（生效中、核验通过禁删） |
| PATCH | `/occupations/{id}/approval` | 审批：`action=approved` 标记占绿 / `rejected` 驳回 |
| PATCH | `/occupations/{id}/restore` | 恢复完成报备（实际恢复面积、苗木恢复情况）→ 待核验 |
| PATCH | `/occupations/{id}/verify` | 恢复核验（核对面积与苗木）通过后解除占绿、恢复考核 |
| GET | `/occupations/summary` | 占绿汇总（按状态、生效面积、到期未恢复数） |
| GET | `/statistics/dashboard` | 看板聚合数据（总览 + 分布 + 趋势 + 榜单 + 提醒 + 占绿提醒） |
| GET | `/statistics/overview` `/distributions` `/trends` `/ranking` `/reminders` | 看板分项接口 |

## 六、业务规则

1. **业务编号**：绿地 `GS-年份-序号`（如 `GS-2026-0001`），任务 `MT-YYYYMMDD-序号`，养护记录 `MR-YYYYMMDD-序号`，更换记录 `PR-YYYYMMDD-序号`，占绿记录 `OC-YYYYMMDD-序号`；留空自动生成，唯一约束冲突时自动重试，编号创建后不可修改。
2. **任务状态联动**（`maintenance_record_service`）：
   - 任务下有养护记录后，任务自动从「待执行」进入「进行中」；
   - 存在**合格**记录且**没有不合格**记录时，任务自动置为「已完成」并写入完成时间；
   - 存在不合格记录时任务保持「进行中」，必须整改复检（把记录改判为合格或删除）后才会完成，手动「标记完成」同样会被拒绝；
   - 删除养护记录后按剩余记录重新推算任务状态，避免出现「已完成却没有记录」；已取消的任务不允许补录记录。
3. **绿地归属一致性**：养护记录可只填绿地（日常养护）或只填任务（绿地自动跟随任务）；两者同时提供时必须属于同一绿地。更换记录若关联养护记录，必须是同一绿地的记录。
4. **日期约束**：养护日期、更换日期不得早于绿地建成日期；占绿开始日期不得早于申请日期、不得早于建成日期，结束日期不得早于开始日期。
5. **金额核算**：更换金额 = 数量 × 单价，由后端统一计算；未填单价时金额留空，前端提示补录。
6. **删除保护**：删除绿地时若已存在任务/记录/更换/占绿数据会返回 409 并给出数量明细，需 `force=true` 才级联删除；但占绿生效中即便强制也不允许删除，必须先完成恢复核验。删除任务时养护记录默认保留（解除关联），避免养护履历丢失；占绿记录生效中、核验通过（审批履历）禁止删除。
7. **字典单一来源**：所有枚举在 `backend/app/constants.py` 定义，前端通过 `/meta/enums` 获取并缓存，前后端不重复维护。
8. **占绿审批与恢复核验**（`occupation_service`）：
   - 流转：待审批 →（通过/驳回）；通过即「占绿中」并在地块上标记占绿，恢复报备后「待核验」，核验通过后解除占绿；
   - 同一绿地同一时间只允许一条生效中的占绿记录，审批第二条会被拒绝；
   - 审批通过但未到占用开始日期不提前标记；占绿中（含到期未恢复）与待核验均视为占绿生效；
   - **占绿期间绿地不参与养护考核**：不计养护逾期、不产生逾期/临期任务提醒、不进入养护工作量排名（`occupied_space_ids` 统一口径）；
   - 恢复核验须满足「实际恢复面积 ≥ 审批占用面积」且「已登记苗木恢复情况」，否则返回差额明细并退回整改，核验通过后绿地重新纳入考核。

## 七、数据模型

| 表 | 说明 | 关键字段 |
| --- | --- | --- |
| `green_space` | 绿地台账 | `code`(唯一)、`name`、`district`、`green_type`、`maintenance_grade`、`area_sqm`、`status`、`manager`、`established_date` |
| `maintenance_task` | 养护任务 | `task_no`(唯一)、`green_space_id`、`task_type`、`plan_date`、`priority`、`executor`、`status`、`completed_at` |
| `maintenance_record` | 养护记录 | `record_no`(唯一)、`task_id`(可空)、`green_space_id`、`record_date`、`work_content`、`worker`、`work_hours`、`weather`、`quality_result` |
| `plant_replacement` | 绿植更换记录 | `replacement_no`(唯一)、`green_space_id`、`maintenance_record_id`(可空)、`plant_name`、`plant_category`、`quantity`、`unit`、`reason`、`unit_price`、`amount` |
| `green_space_occupation` | 占绿审批与恢复核验 | `occupation_no`(唯一)、`green_space_id`、`reason`、`purpose`、`occupy_area_sqm`、`start_date`、`end_date`、`restore_requirement`、`status`、审批信息（`approved_by`/`approved_at`）、恢复报备（`restored_date`/`restored_area_sqm`/`restored_plants`）、核验信息（`verified_by`/`verified_at`） |

绿地删除时任务/记录/更换/占绿级联清理；任务与养护记录之间、养护记录与更换记录之间为可空外键（`SET NULL`），保证养护履历可独立留存。绿地是否处于占绿状态由生效中的占绿记录动态推导（占绿中且已到开始日期，或待核验），不额外落库冗余字段。

## 八、测试

```bash
cd backend
python -m pytest              # 79 个用例：接口、校验、跨模块规则、端到端流程、占绿审批与恢复核验
```

覆盖重点：绿地编号生成与唯一性、枚举与字段校验、列表过滤/排序/分页、任务状态自动流转与手动流转限制、记录删除后的状态回退、更换金额核算、删除保护与强制删除、统计聚合口径一致性、演示数据自洽性、占绿审批流转与同绿地互斥、占绿状态标记、占绿期间养护考核豁免（逾期提醒/排名/绿地档案）、恢复面积与苗木核验及退回整改、占绿删除保护。

## 九、常见问题

- **前端页面正常但数据为空**：确认后端已启动且 `/api/v1/meta/health` 返回 `database: up`；容器方式下检查 `docker compose ps` 中 backend 是否 `healthy`。
- **端口被占用**：修改 `.env` 中的 `FRONTEND_PORT` / `BACKEND_PORT`，或在本地开发时用 `flask --app wsgi run --port 5001` 并同步调整 `VITE_PROXY_TARGET`。
- **数据库结构变更**：切换 `AUTO_CREATE_TABLES=false` 后使用 Flask-Migrate：`flask --app wsgi db init && flask --app wsgi db migrate -m "描述" && flask --app wsgi db upgrade`。
- **重置演示数据**：`flask --app wsgi seed --reset`；容器方式可执行 `docker compose exec backend flask --app wsgi seed --reset`。

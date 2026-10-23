# 本色 · MBTI 性格探索

Flask + MySQL + 原生 HTML/CSS/JavaScript，包含简版与完整版测试、注册登录、管理员审核、个人中心和测试历史。

## 启动

需要 Python 3.10+ 和 MySQL 8.x。

```powershell
python -m pip install -r requirements.txt
# 首次部署时复制模板；当前工作区已创建 config.ini，请勿覆盖。
# Copy-Item config.example.ini config.ini
python -m flask --app app init-db
python -m flask --app app create-admin
python app.py
```

当前工作区也可使用 `.\.venv\Scripts\python.exe` 替换上述 `python`。

打开 http://127.0.0.1:5000 。`create-admin` 在终端交互询问用户名、邮箱、密码，不提供默认管理员密码；不需要将管理员密码写入源代码。管理员使用普通登录入口登录后，顶部会出现“管理员审核”。

`init-db` 仅创建配置的数据库和缺失表，不清空已有数据。表结构已有变更的部署应单独执行经过确认的迁移，`create_all` 不修改既有列。

## 超级管理员登录

当前工作区已在 MySQL 中创建 `superadmin` 超级管理员。初始密码保存在本机 `instance/superadmin-credentials.txt`（被 Git 忽略），未写入代码。启动服务后打开 `http://127.0.0.1:5000/#login`，使用该账号登录；可以在个人中心修改密码。

超级管理员在“管理员审核 → 已通过”中，可以为已审核用户授予或取消管理员权限；普通管理员可以审核注册、重试通知、重置普通用户密码和切换账号状态，不能修改管理员权限。权限变化会使目标用户的旧会话失效。网页不能降级超级管理员，也不能通过注册请求创建管理员。

其他部署环境可通过以下命令创建超级管理员（交互设置密码）：

```powershell
python -m flask --app app create-superadmin
```

## 数据库配置

编辑项目根目录 `config.ini`：

```ini
[database]
host = 127.0.0.1
port = 3306
user = root
password = 你的MySQL密码
name = mbti
```

当前工作区已填入用户提供的数据库密码并初始化数据库。`config.ini`、`.venv/`、`instance/` 均已加入 `.gitignore`；可提交的 `config.example.ini` 不包含真实密码。

支持通过 `MBTI_CONFIG` 指定其他 ini 文件，通过 `MBTI_DB_PASSWORD` 覆盖数据库密码。数据库使用 utf8mb4，可保存中文与 Emoji。

## 注册、审核与登录

注册、修改密码和管理员重置的新密码长度统一为 **8–20 位**。为兼容已有账号，登录仍接受此前设置的较长密码，不会修改超级管理员的现有密码。

1. 用户填写用户名、邮箱和密码，提交后状态为“待审核”。
2. 服务端将申请和邮件通知记录一起写入数据库，然后发送邮件到 `qiwen421@outlook.com`。
3. 管理员登录后，在审核界面查看申请并通过或拒绝；拒绝时需填写原因。
4. 只有通过审核的账号可以登录和提交测试，审核决定、审核人和审核时间会被保存。
5. SMTP 不可用时，注册申请仍然保留。页面明确告知邮件未发送，管理员可在审核界面重试。

## 管理员：用户状态、密码重置与多选

管理员页面默认显示全部用户，并支持按审核状态及账号状态筛选。

- **激活 / 封闭**是账号使用状态，与“待审核 / 已通过 / 已拒绝”分开保存；激活不会绕过注册审核。
- 封闭账号无法登录，已有会话失效；重新激活后可以使用原密码登录，历史测试记录保留。
- 每个可管理用户都有“重置密码”按钮，可以直接设置 8–20 位新密码，无需原密码；成功后用户原会话失效、登录错误锁定清除。
- 可逐个勾选或“全选本页可管理用户”，进行批量激活、批量封闭或批量重置密码。翻页或改变筛选后清空选择。
- 批量重置会为每个账号生成不同的随机密码，结果只在本次弹窗展示，可下载清单。服务端仅保存密码哈希，不保存明文密码清单。
- 普通管理员可管理普通用户；超级管理员还可管理普通管理员。不能通过这些操作封闭自己、重置自己的密码或操作超级管理员；自身改密仍在个人中心完成。
- 批次会先校验全部用户，发现不存在或无权管理的账号时整批不作修改。

已有部署需在重启前执行一次数据库迁移（当前工作区已完成）：

```powershell
python -m flask --app app migrate-db
```

此命令仅给 `users` 添加 `account_state` 字段，原账号默认激活；保留原密码、审核状态和测试结果，可以重复运行。

这里的“审核”是管理员人工批准账号，不是向注册用户发送验证码。用户填写的邮箱未经过邮箱所有权验证。邮件不包含密码或密码哈希，也不能通过邮件链接直接批准账号。

## Outlook OAuth2 邮件设置

当前 `config.ini` 保留 Outlook OAuth2 模式，收件人已配置为 `qiwen421@outlook.com`。发件人暂按同一邮箱预填，若使用其他 Outlook 邮箱，请同时修改 `username`、`sender`。

```ini
[mail]
admin_email = qiwen421@outlook.com
host = smtp-mail.outlook.com
port = 587
username = qiwen421@outlook.com
sender = qiwen421@outlook.com
security = starttls
auth = oauth2
password =
oauth_token =
oauth_client_id =
oauth_client_secret =
oauth_refresh_token =
oauth_tenant = consumers
```

Outlook.com 使用 OAuth2。需要在 Microsoft Entra 注册支持个人 Microsoft 账号的应用，按授权码或设备授权流程由邮箱所有者授权 `https://outlook.office.com/SMTP.Send`，并请求 `offline_access` 来获取刷新令牌。

- 推荐填写 `oauth_client_id` 和 `oauth_refresh_token`。需要客户端机密的应用再填写 `oauth_client_secret`；公开客户端可留空。
- 程序会使用刷新令牌获取访问令牌，并将更新后的令牌写入 `instance/outlook_tokens.json`。令牌即将到期时自动续期；重启仍可读取缓存。
- 也支持只填写 `oauth_token`，但它到期后需要手动更新，不能使用普通邮箱密码代替。
- 如果更换发件应用或需要强制使用新刷新令牌，停服务后移除本机 `instance/outlook_tokens.json` 缓存，再重新启动。
- 如使用组织 Microsoft 365 邮箱，请按服务商设置修改 SMTP 主机及租户 ID，并确保邮箱允许 OAuth SMTP AUTH。
- 可用 `MBTI_MAIL_OAUTH_TOKEN`、`MBTI_MAIL_REFRESH_TOKEN`、`MBTI_MAIL_CLIENT_SECRET` 环境变量覆盖对应凭据。

**当前未提供 OAuth 凭据，真实邮件发送尚未验证。** 填写后重启服务，可在管理员界面重试失败通知，或运行：

```powershell
python -m flask --app app retry-mail
```

参考：[Microsoft Outlook.com SMTP 设置](https://support.microsoft.com/en-us/outlook/pop-imap-and-smtp-settings-for-outlook-com)、[Microsoft OAuth2 SMTP 认证](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth)。

## 测试记录与个人中心

- 简版 20 题，完整版 60 题（每维度 15 题），四维题目交错展示。
- 开始测试时由服务器记录开始时间；提交成功后记录完成时间、测试版本、原始答案和完整结果快照。
- 同一次测试的网络重试不会重复生成历史记录；重新开始测试会创建新记录。
- 个人中心按完成时间倒序展示历史，支持分页和查看每次报告；报告链接刷新后仍可恢复。
- 记录接口只能读取登录账号自己的结果，管理员审核权限不包含读取他人的测试结果。
- 时间在数据库中统一以 UTC 保存，API 输出带时区时间，页面按浏览器本地时区展示。
- 未完成的答题进度按账号隔离保存于当前浏览器；正式结果持久保存于 MySQL。
- 修改密码需输入当前密码；修改后当前会话及其他设备的旧会话失效，需重新登录。

## 数据表

| 表 | 内容 |
| --- | --- |
| users | 用户、密码哈希、审核状态、激活/封闭状态、审核人和时间、会话版本 |
| test_attempts | 测试版本、账号和服务器开始时间 |
| test_results | 账号对应的每次测试完成时间、答案、结果快照 |
| mail_notifications | 注册通知、发送状态、尝试次数、失败信息 |

密码使用 Werkzeug 的 scrypt 哈希；Cookie 为 HttpOnly、SameSite=Lax；修改类 API 校验 CSRF；登录连续输错 5 次锁定 15 分钟。会话随机密钥默认保存在 `instance/secret_key`，部署多进程或多实例时需共享同一个密钥；可通过 `MBTI_SECRET_KEY` 配置。HTTPS 部署时将 `[app] secure_cookie` 改为 `true`，并设置真实的 `base_url`，让邮件指向正确地址。

## 验证

```powershell
python -m unittest test_accounts test_mbti -v
node --check static/js/account.js
node --check static/js/app.js
# 对配置的真实 MySQL 执行完整集成检查；测试数据全部事务回滚，不发真实邮件。
python scripts/check_mysql.py
```

单元测试使用隔离 SQLite；真实 MySQL 集成检查覆盖注册、审核、登录、两种测试入库、JSON 报告、历史、重复提交和修改密码。

## 主要文件

- `config.ini` / `config.example.ini` / `config.py`：本地设置、可提交模板、读取逻辑。
- `models/database.py`：数据库模型。
- `api/controllers/account_controller.py`：账号、历史、审核接口。
- `api/controllers/mbti_controller.py`：创建测试和保存结果。
- `services/auth_service.py`：鉴权、会话和 CSRF。
- `services/mail_service.py` / `services/oauth_service.py`：SMTP 通知与 Outlook 令牌续期。
- `templates/index.html`、`static/css/style.css`：所有页面和样式。
- `static/js/account.js` / `static/js/app.js`：账号页面和测试交互。

本测试是原创 MBTI 风格自我探索问卷，不是官方 MBTI 量表或心理诊断。

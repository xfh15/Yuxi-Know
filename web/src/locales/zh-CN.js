export default {
  common: {
    retry: '重试',
    login: '登录',
    logout: '退出登录',
    loggedOutSuccess: '已退出登录',
    close: '关闭',
    save: '保存',
    cancel: '取消',
    upload: '上传',
    uploadAvatar: '上传头像',
    changeAvatar: '更换头像',
    notSet: '未设置',
    contactUs: '联系我们',
    help: '使用帮助',
    allRightsReserved: 'All Rights Reserved.',
    backToLogin: '返回登录页',
    language: '语言',
    darkMode: '切换到深色模式 (Beta)',
    lightMode: '切换到浅色模式',
    documentationCenter: '文档中心',
    systemSettings: '系统设置',
    debugPanel: '调试面板',
    debugPanelNonProd: '调试面板（非生产环境）',
    taskCenter: '任务中心',
    githubStar: '欢迎 Star',
    duration: {
      seconds: '{count}秒',
      minutesSeconds: '{minutes}分{seconds}秒',
      hoursMinutes: '{hours}小时{minutes}分钟',
      daysHours: '{days}天{hours}小时'
    }
  },
  layout: {
    nav: {
      agent: '智能体',
      knowledge: '知识库',
      extensions: '扩展管理',
      dashboard: 'Dashboard'
    }
  },
  home: {
    connectingService: '正在连接服务...',
    serviceConnectionFailed: '服务连接失败',
    backendUnavailable: '后端服务无法响应，请检查服务是否正常运行',
    startExperience: '开始体验',
    viewDocs: '查看文档',
    heroBadge: '已获得 {count} GitHub Stars',
    heroBadgeNoCount: '已获得 GitHub Stars',
    faq: '常见问题',
    loadFailed: '加载失败',
    serviceUnavailable: '服务不可用'
  },
  auth: {
    serverConnectionFailed: '服务端连接失败',
    welcomeLogin: '欢迎登录',
    initTitle: '系统初始化，请创建超级管理员',
    userId: '用户ID',
    userIdPlaceholder: '请输入用户ID（3-20个字符）',
    phoneOptional: '手机号（可选）',
    phonePlaceholder: '可用于登录，可不填写',
    loginBackgroundAlt: '登录背景',
    password: '密码',
    confirmPassword: '确认密码',
    loginAccount: '登录账号',
    loginAccountPlaceholder: '用户ID或手机号',
    agreePrefix: '登录即代表同意',
    userAgreement: '《用户协议》',
    privacyPolicy: '《隐私协议》',
    createAdminAccount: '创建管理员账户',
    lockedLabel: '账户已锁定 {time}',
    orUseFollowing: '或使用以下方式登录',
    oidcLogin: 'OIDC 登录',
    loginSuccess: '登录成功',
    loginFailed: '登录失败',
    loginFailedRetry: '登录失败，请检查用户名和密码',
    accountLockedWait: '账户被锁定，请等待 {time}',
    accountLockedForFailures: '由于多次登录失败，账户已被锁定 {time}',
    accountLockedRetryLater: '账户被锁定，请稍后再试',
    getOidcConfigFailed: '获取 OIDC 配置失败',
    getOidcLoginUrlFailed: '获取 OIDC 登录地址失败',
    oidcLoginFailedRetry: 'OIDC 登录失败，请重试',
    adminCreated: '管理员账户创建成功',
    initFailedRetry: '初始化失败，请重试',
    systemErrorRetry: '系统出错，请稍后重试',
    serviceStatusError: '服务端状态异常',
    serviceConnectError: '无法连接到服务端，请检查网络连接',
    processingLogin: '正在处理登录...',
    processingLoginError: '处理登录请求时发生错误',
    processingLoginErrorRetry: '处理登录请求时发生错误，请重试',
    invalidParams: '参数错误',
    missingLoginCode: '缺少有效的登录 code，请重新登录',
    redirecting: '正在跳转...',
    createPasswordConfirm: '两次输入的密码不一致',
    pleaseConfirmPassword: '请确认密码',
    usernameRequired: '请输入用户ID',
    usernamePattern: '用户ID只能包含字母、数字和下划线',
    usernameLength: '用户ID长度必须在3-20个字符之间',
    phoneInvalid: '请输入正确的手机号格式',
    passwordRequired: '请输入密码',
    loginIdRequired: '请输入用户ID或手机号',
    agreementRequired: '请先阅读并同意《用户协议》《隐私协议》'
  },
  user: {
    superadmin: '超级管理员',
    admin: '管理员',
    user: '普通用户',
    unknownRole: '未知角色',
    username: '用户名',
    phoneNumber: '手机号',
    role: '角色',
    department: '部门',
    defaultDepartment: '默认部门',
    editProfile: '编辑资料',
    fetchCurrentUserFailed: '获取用户信息失败',
    fetchUsersFailed: '获取用户列表失败',
    createUserFailed: '创建用户失败',
    updateUserFailed: '更新用户失败',
    deleteUserFailed: '删除用户失败',
    validateUsernameFailed: '用户名验证失败',
    avatarUploadFailedFallback: '头像上传失败',
    profileUpdated: '个人资料更新成功！',
    updateProfileFailedFallback: '更新个人资料失败',
    profileUpdateFailed: '更新失败：{message}',
    usernameLengthHint: '用户名长度必须在 2-20 个字符之间',
    phoneInvalid: '请输入正确的手机号格式',
    avatarFormatHint: '支持 JPG、PNG 格式，文件不超过 5MB',
    avatarUploadSuccess: '头像上传成功！',
    avatarUploadFailed: '头像上传失败：{message}',
    avatarOnlyImage: '只能上传图片文件！',
    avatarSizeLimit: '图片大小不能超过 5MB！'
  },
  errors: {
    userNotLoggedIn: '用户未登录',
    loginExpired: '登录已过期，请重新登录',
    authFailedRelogin: '认证失败，请重新登录',
    permissionDenied: '没有权限执行此操作',
    serverInternalLogs: '服务器内部错误，请使用 docker logs api-dev 查看详细日志',
    operationFailed: '{context}失败',
    operationFailedWithMessage: '{context}失败: {message}',
    networkConnectionFailed: '网络连接失败，请检查网络设置',
    resourceNotFound: '请求的资源不存在',
    serverErrorRetry: '服务器错误，请稍后重试',
    contexts: {
      operation: '操作',
      networkRequest: '网络请求',
      sendMessage: '发送消息',
      createConversation: '创建对话',
      deleteConversation: '删除对话',
      renameConversation: '重命名对话',
      loadConversation: '加载对话',
      exportConversation: '导出对话',
      streamProcessing: '流式处理',
      inputValidation: '输入验证'
    }
  },
  toolCalls: {
    summary: {
      single: '使用了工具: {tool}',
      multiple: '已调用 {count} 个工具'
    },
    status: {
      completed: '已完成',
      failedCount: '{count} 失败',
      runningCount: '{count} 进行中'
    },
    base: {
      success: '工具 {tool} 执行完成',
      error: '工具 {tool} 执行失败',
      running: '正在调用工具: {tool}',
      params: '参数'
    },
    labels: {
      knowledgeBase: '知识库',
      knowledgeBaseList: '知识库列表',
      knowledgeBaseSearch: '知识库搜索',
      knowledgeGraph: '知识图谱',
      mindmap: '思维导图',
      webSearch: '网络搜索',
      askUserQuestion: '提问',
      todo: '待办',
      mysqlQuery: '执行 SQL 查询',
      mysqlDescribeTable: '描述表结构',
      mysqlListTables: '列出数据库表'
    },
    askUserQuestion: {
      noQuestion: '无问题',
      answered: '已回答',
      other: '其他: {text}',
      multipleQuestions: '{question} 等 {count} 题'
    },
    listKbs: {
      count: '共 {count} 个知识库',
      noDescription: '无描述',
      empty: '暂无知识库',
      summary: '{count}个知识库：{names}',
      summaryWithMore: '{count}个知识库：{names} 等{remaining}个'
    },
    queryKb: {
      kbLabel: '知识库: {name}',
      graphSummary: '图谱检索: 实体 {entities} 个, 关系 {relationships} 条, 引用 {references} 条',
      entities: '实体',
      relationships: '关系',
      references: '引用',
      related: '关联',
      empty: '未找到相关知识库内容',
      unnamedEntity: '未命名实体',
      uncategorized: '未分类'
    },
    webSearch: {
      empty: '未找到相关搜索结果'
    },
    todo: {
      inProgress: '进行中: {content}',
      pending: '待处理: {content}',
      updated: '更新: {content}',
      empty: '暂无待办事项'
    },
    grep: {
      matchedFiles: '共匹配 {count} 个文件',
      matchedLines: '共匹配 {count} 行',
      lineNumber: '第 {line} 行',
      empty: '未找到匹配结果'
    },
    knowledgeGraph: {
      summary: '找到 {nodes} 个节点, {relations} 个关系',
      refresh: '重新渲染图谱'
    },
    mysql: {
      executeQuery: '执行SQL查询：',
      describeTable: '描述表结构：',
      listTables: '列出数据库表'
    }
  }
}

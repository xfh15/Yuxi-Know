export default {
  common: {
    retry: 'Retry',
    login: 'Log in',
    logout: 'Log out',
    loggedOutSuccess: 'Logged out successfully',
    close: 'Close',
    save: 'Save',
    cancel: 'Cancel',
    upload: 'Upload',
    uploadAvatar: 'Upload avatar',
    changeAvatar: 'Change avatar',
    notSet: 'Not set',
    contactUs: 'Contact us',
    help: 'Help',
    allRightsReserved: 'All Rights Reserved.',
    backToLogin: 'Back to login',
    language: 'Language',
    darkMode: 'Switch to dark mode (Beta)',
    lightMode: 'Switch to light mode',
    systemSettings: 'System settings',
    debugPanel: 'Debug panel',
    debugPanelNonProd: 'Debug panel (non-production)',
    taskCenter: 'Task center',
    duration: {
      seconds: '{count}s',
      minutesSeconds: '{minutes}m {seconds}s',
      hoursMinutes: '{hours}h {minutes}m',
      daysHours: '{days}d {hours}h'
    }
  },
  layout: {
    nav: {
      agent: 'Agent',
      knowledge: 'Knowledge',
      extensions: 'Extensions',
      dashboard: 'Dashboard'
    }
  },
  home: {
    connectingService: 'Connecting to service...',
    serviceConnectionFailed: 'Service connection failed',
    backendUnavailable: 'The backend service is not responding. Check whether it is running.',
    startExperience: 'Get started',
    viewDocs: 'View docs',
    heroBadge: '{count} GitHub Stars',
    heroBadgeNoCount: 'GitHub Stars',
    faq: 'FAQ',
    loadFailed: 'Load failed',
    serviceUnavailable: 'Service unavailable'
  },
  auth: {
    serverConnectionFailed: 'Backend connection failed',
    welcomeLogin: 'Welcome back',
    initTitle: 'System initialization: create the super admin',
    userId: 'User ID',
    userIdPlaceholder: 'Enter a user ID (3-20 characters)',
    phoneOptional: 'Phone number (optional)',
    phonePlaceholder: 'Can be used for login',
    loginBackgroundAlt: 'Login background',
    password: 'Password',
    confirmPassword: 'Confirm password',
    loginAccount: 'Login account',
    loginAccountPlaceholder: 'User ID or phone number',
    agreePrefix: 'By logging in you agree to',
    userAgreement: 'User Agreement',
    privacyPolicy: 'Privacy Policy',
    createAdminAccount: 'Create admin account',
    lockedLabel: 'Account locked {time}',
    orUseFollowing: 'Or sign in with',
    oidcLogin: 'OIDC sign in',
    loginSuccess: 'Login successful',
    loginFailed: 'Login failed',
    loginFailedRetry: 'Login failed. Check your user ID and password.',
    accountLockedWait: 'This account is locked. Please wait {time}.',
    accountLockedForFailures: 'Too many failed attempts. Account locked for {time}.',
    accountLockedRetryLater: 'This account is locked. Please try again later.',
    getOidcConfigFailed: 'Failed to load the OIDC configuration',
    getOidcLoginUrlFailed: 'Failed to get the OIDC login URL',
    oidcLoginFailedRetry: 'OIDC login failed. Please try again.',
    adminCreated: 'Admin account created successfully',
    initFailedRetry: 'Initialization failed. Please try again.',
    systemErrorRetry: 'A system error occurred. Please try again later.',
    serviceStatusError: 'Unexpected backend status',
    serviceConnectError: 'Unable to connect to the backend service. Check your network connection.',
    processingLogin: 'Processing login...',
    processingLoginError: 'An error occurred while processing the login request',
    processingLoginErrorRetry: 'An error occurred while processing the login request. Please try again.',
    invalidParams: 'Invalid parameters',
    missingLoginCode: 'Missing a valid login code. Please sign in again.',
    redirecting: 'Redirecting...',
    createPasswordConfirm: 'The two passwords do not match',
    pleaseConfirmPassword: 'Please confirm the password',
    usernameRequired: 'Please enter a user ID',
    usernamePattern: 'User ID can only contain letters, numbers, and underscores',
    usernameLength: 'User ID must be between 3 and 20 characters',
    phoneInvalid: 'Enter a valid phone number',
    passwordRequired: 'Please enter a password',
    loginIdRequired: 'Please enter a user ID or phone number',
    agreementRequired: 'Please read and accept the User Agreement and Privacy Policy first'
  },
  user: {
    superadmin: 'Super admin',
    admin: 'Admin',
    user: 'User',
    unknownRole: 'Unknown role',
    username: 'Username',
    phoneNumber: 'Phone number',
    role: 'Role',
    department: 'Department',
    defaultDepartment: '部門1',
    editProfile: 'Edit profile',
    fetchCurrentUserFailed: 'Failed to load user information',
    fetchUsersFailed: 'Failed to load the user list',
    createUserFailed: 'Failed to create the user',
    updateUserFailed: 'Failed to update the user',
    deleteUserFailed: 'Failed to delete the user',
    validateUsernameFailed: 'Failed to validate the username',
    avatarUploadFailedFallback: 'Failed to upload the avatar',
    profileUpdated: 'Profile updated successfully!',
    updateProfileFailedFallback: 'Failed to update the profile',
    profileUpdateFailed: 'Update failed: {message}',
    usernameLengthHint: 'Username must be between 2 and 20 characters',
    phoneInvalid: 'Enter a valid phone number',
    avatarFormatHint: 'Supports JPG and PNG, up to 5 MB',
    avatarUploadSuccess: 'Avatar uploaded successfully!',
    avatarUploadFailed: 'Avatar upload failed: {message}',
    avatarOnlyImage: 'Only image files are allowed!',
    avatarSizeLimit: 'Image size must be smaller than 5 MB!'
  },
  errors: {
    userNotLoggedIn: 'User is not logged in',
    loginExpired: 'Your session has expired. Please log in again.',
    authFailedRelogin: 'Authentication failed. Please log in again.',
    permissionDenied: 'You do not have permission to perform this action',
    serverInternalLogs: 'Internal server error. Use docker logs api-dev for details.',
    operationFailed: '{context} failed',
    operationFailedWithMessage: '{context} failed: {message}',
    networkConnectionFailed: 'Network connection failed. Check your network settings.',
    resourceNotFound: 'The requested resource was not found',
    serverErrorRetry: 'Server error. Please try again later.',
    contexts: {
      operation: 'Operation',
      networkRequest: 'Network request',
      sendMessage: 'Send message',
      createConversation: 'Create conversation',
      deleteConversation: 'Delete conversation',
      renameConversation: 'Rename conversation',
      loadConversation: 'Load conversation',
      exportConversation: 'Export conversation',
      streamProcessing: 'Stream processing',
      inputValidation: 'Input validation'
    }
  },
  toolCalls: {
    summary: {
      single: 'Used tool: {tool}',
      multiple: 'Called {count} tools'
    },
    status: {
      completed: 'Completed',
      failedCount: '{count} failed',
      runningCount: '{count} running'
    },
    base: {
      success: 'Tool {tool} completed',
      error: 'Tool {tool} failed',
      running: 'Calling tool: {tool}',
      params: 'Parameters'
    },
    labels: {
      knowledgeBase: 'Knowledge base',
      knowledgeBaseList: 'Knowledge base list',
      knowledgeBaseSearch: 'Knowledge base search',
      knowledgeGraph: 'Knowledge graph',
      mindmap: 'Mind map',
      webSearch: 'Web search',
      askUserQuestion: 'Question',
      todo: 'Todo',
      mysqlQuery: 'Execute SQL query',
      mysqlDescribeTable: 'Describe table schema',
      mysqlListTables: 'List database tables'
    },
    askUserQuestion: {
      noQuestion: 'No question',
      answered: 'Answered',
      other: 'Other: {text}',
      multipleQuestions: '{question} and {count} more'
    },
    listKbs: {
      count: '{count} knowledge bases',
      noDescription: 'No description',
      empty: 'No knowledge bases',
      summary: '{count} knowledge bases: {names}',
      summaryWithMore: '{count} knowledge bases: {names} and {remaining} more'
    },
    queryKb: {
      kbLabel: 'Knowledge base: {name}',
      graphSummary:
        'Graph search: {entities} entities, {relationships} relationships, {references} references',
      entities: 'Entities',
      relationships: 'Relationships',
      references: 'References',
      related: 'Related',
      empty: 'No relevant knowledge base content found',
      unnamedEntity: 'Unnamed entity',
      uncategorized: 'Uncategorized'
    },
    webSearch: {
      empty: 'No relevant search results found'
    },
    todo: {
      inProgress: 'In progress: {content}',
      pending: 'Pending: {content}',
      updated: 'Updated: {content}',
      empty: 'No todo items'
    },
    grep: {
      matchedFiles: '{count} matching files',
      matchedLines: '{count} matching lines',
      lineNumber: 'Line {line}',
      empty: 'No matches found'
    },
    knowledgeGraph: {
      summary: 'Found {nodes} nodes and {relations} relationships',
      refresh: 'Render graph again'
    },
    mysql: {
      executeQuery: 'Execute SQL query:',
      describeTable: 'Describe table schema:',
      listTables: 'List database tables'
    }
  }
}

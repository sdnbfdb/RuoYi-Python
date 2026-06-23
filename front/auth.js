// 用户认证状态管理模块
const Auth = {
    // localStorage key
    STORAGE_KEY: 'ruoyi_user',
    TOKEN_KEY: 'ruoyi_token',

    // 获取当前用户信息
    getUser() {
        const userStr = localStorage.getItem(this.STORAGE_KEY);
        return userStr ? JSON.parse(userStr) : null;
    },

    // 获取 Token
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    // 保存用户信息
    setUser(user, token) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(user));
        if (token) {
            localStorage.setItem(this.TOKEN_KEY, token);
        }
    },

    // 检查是否已登录
    isLoggedIn() {
        const user = this.getUser();
        const token = this.getToken();
        return !!(user && token);
    },

    // 清除登录信息（登出）
    logout() {
        localStorage.removeItem(this.STORAGE_KEY);
        localStorage.removeItem(this.TOKEN_KEY);
        // 跳转到登录页
        window.location.href = 'login.html';
    },

    // 获取用户显示名称
    getUserName() {
        const user = this.getUser();
        return user ? (user.name || user.username || user.account) : null;
    },

    // 获取用户账号
    getAccount() {
        const user = this.getUser();
        return user ? user.account : null;
    },

    // 获取用户ID
    getUserId() {
        const user = this.getUser();
        return user ? user.id : null;
    }
};

// 页面加载时检查登录状态（需要登录的页面调用）
function requireAuth(redirectUrl = 'login.html') {
    if (!Auth.isLoggedIn()) {
        alert('请先登录！');
        window.location.href = redirectUrl;
        return false;
    }
    return true;
}

// 更新页面上的用户信息显示
function updateUserDisplay() {
    const user = Auth.getUser();
    if (!user) return;

    // 更新用户名
    const userNameElements = document.querySelectorAll('.user-name');
    userNameElements.forEach(el => {
        el.textContent = user.name || user.username || user.account;
    });

    // 更新账号
    const accountElements = document.querySelectorAll('.user-account');
    accountElements.forEach(el => {
        el.textContent = user.account;
    });

    // 更新用户ID
    const userIdElements = document.querySelectorAll('.user-id');
    userIdElements.forEach(el => {
        el.textContent = `ID: ${user.id || user.account}`;
    });
}

// 认证模块（用于页面调用）
const AuthModule = {
    // API 基础地址
    API_BASE: 'http://localhost:5000',

    // 检查登录状态
    isLoggedIn() {
        return Auth.isLoggedIn();
    },

    // 获取用户信息
    getUserInfo() {
        return Auth.getUser();
    },

    // 获取 Token
    getToken() {
        return Auth.getToken();
    },

    // 获取用户显示名称
    getUserName() {
        return Auth.getUserName();
    },

    // 退出登录
    logout() {
        Auth.logout();
    },

    // 更新个人信息
    async updateProfile(data) {
        const token = this.getToken();
        if (!token) {
            return { success: false, message: '未登录' };
        }

        try {
            const response = await fetch(`${this.API_BASE}/api/auth/profile/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                return { success: true, data: result.data };
            } else {
                return { success: false, message: result.message || '更新失败' };
            }
        } catch (error) {
            console.error('更新个人信息失败:', error);
            return { success: false, message: '网络错误，请稍后重试' };
        }
    },

    // 修改密码
    async changePassword(currentPassword, newPassword) {
        const token = this.getToken();
        if (!token) {
            return { success: false, message: '未登录' };
        }

        try {
            const response = await fetch(`${this.API_BASE}/api/auth/password/change`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    currentPassword,
                    newPassword
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                return { success: true };
            } else {
                return { success: false, message: result.message || '密码修改失败' };
            }
        } catch (error) {
            console.error('修改密码失败:', error);
            return { success: false, message: '网络错误，请稍后重试' };
        }
    }
};

// 兼容ES6模块和传统script标签引入
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Auth, AuthModule, requireAuth, updateUserDisplay };
}

// 尝试ES6 export（如果支持）
if (typeof window !== 'undefined') {
    // 将Auth对象暴露到全局作用域，供传统script标签使用
    window.Auth = Auth;
    window.AuthModule = AuthModule;
    window.requireAuth = requireAuth;
    window.updateUserDisplay = updateUserDisplay;
}

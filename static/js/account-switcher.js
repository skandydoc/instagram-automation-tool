// Account Switcher and Multi-Account Management

class AccountManager {
    constructor() {
        this.currentAccountId = this.getCurrentAccountId();
        this.selectedAccounts = new Set();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadAccountSwitcher();
        this.updateUIForCurrentAccount();
    }

    getCurrentAccountId() {
        // Get from localStorage or default to 'all'
        return localStorage.getItem('currentAccountId') || 'all';
    }

    setCurrentAccountId(accountId) {
        this.currentAccountId = accountId;
        localStorage.setItem('currentAccountId', accountId);
        this.updateUIForCurrentAccount();
        
        // Reload page data for the selected account
        if (window.location.pathname === '/') {
            this.loadDashboardForAccount(accountId);
        }
    }

    setupEventListeners() {
        // Account switcher dropdown
        document.addEventListener('click', (e) => {
            if (e.target.closest('.account-switch-item')) {
                const accountId = e.target.closest('.account-switch-item').dataset.accountId;
                this.setCurrentAccountId(accountId);
            }
        });

        // Bulk account selection
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('account-select-checkbox')) {
                const accountId = e.target.value;
                if (e.target.checked) {
                    this.selectedAccounts.add(accountId);
                } else {
                    this.selectedAccounts.delete(accountId);
                }
                this.updateBulkOperationsUI();
            }
        });

        // Select all accounts
        const selectAllBtn = document.getElementById('selectAllAccounts');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('.account-select-checkbox');
                const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                
                checkboxes.forEach(cb => {
                    cb.checked = !allChecked;
                    if (cb.checked) {
                        this.selectedAccounts.add(cb.value);
                    } else {
                        this.selectedAccounts.delete(cb.value);
                    }
                });
                
                this.updateBulkOperationsUI();
            });
        }
    }

    async loadAccountSwitcher() {
        try {
            const response = await fetch('/api/accounts');
            const accounts = await response.json();
            
            const switcher = document.getElementById('accountSwitcher');
            if (!switcher) return;

            const currentAccount = accounts.find(a => a.id === this.currentAccountId) || { username: 'All Accounts' };
            
            switcher.innerHTML = `
                <div class="dropdown account-switcher">
                    <button class="dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <div class="account-avatar">${this.getAccountInitials(currentAccount.username)}</div>
                        <span>${currentAccount.username}</span>
                        <i class="fas fa-chevron-down"></i>
                    </button>
                    <ul class="dropdown-menu">
                        <li>
                            <div class="account-switch-item account-item ${this.currentAccountId === 'all' ? 'active' : ''}" data-account-id="all">
                                <div class="account-avatar" style="background-color: #6c757d;">
                                    <i class="fas fa-users"></i>
                                </div>
                                <div class="account-info">
                                    <p class="account-name">All Accounts</p>
                                    <p class="account-stats">${accounts.length} accounts</p>
                                </div>
                            </div>
                        </li>
                        <li><hr class="dropdown-divider"></li>
                        ${accounts.map(account => `
                            <li>
                                <div class="account-switch-item account-item ${this.currentAccountId === account.id.toString() ? 'active' : ''}" data-account-id="${account.id}">
                                    <div class="account-avatar">${this.getAccountInitials(account.username)}</div>
                                    <div class="account-info">
                                        <p class="account-name">@${account.username}</p>
                                        <p class="account-stats">${account.posts_count || 0} posts • ${account.is_active ? 'Active' : 'Inactive'}</p>
                                    </div>
                                </div>
                            </li>
                        `).join('')}
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <a class="dropdown-item" href="/add_account">
                                <i class="fas fa-plus-circle"></i> Add New Account
                            </a>
                        </li>
                    </ul>
                </div>
            `;
        } catch (error) {
            console.error('Error loading account switcher:', error);
        }
    }

    getAccountInitials(username) {
        if (!username) return 'U';
        if (username.startsWith('@')) username = username.substring(1);
        return username.substring(0, 2).toUpperCase();
    }

    updateUIForCurrentAccount() {
        // Update page title
        if (this.currentAccountId === 'all') {
            document.title = 'All Accounts - Instagram Automation';
        } else {
            const accountName = document.querySelector(`.account-switch-item[data-account-id="${this.currentAccountId}"] .account-name`)?.textContent || 'Account';
            document.title = `${accountName} - Instagram Automation`;
        }

        // Update active states
        document.querySelectorAll('.account-switch-item').forEach(item => {
            if (item.dataset.accountId === this.currentAccountId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    async loadDashboardForAccount(accountId) {
        // Show loading state
        const mainContent = document.querySelector('.main-content');
        const contentArea = mainContent.querySelector('.content-area');
        if (contentArea) {
            contentArea.innerHTML = '<div class="text-center p-5"><div class="loading-spinner"></div><p>Loading account data...</p></div>';
        }

        try {
            const endpoint = accountId === 'all' ? '/api/dashboard/all' : `/api/dashboard/${accountId}`;
            const response = await fetch(endpoint);
            const data = await response.json();
            
            // Update dashboard with account-specific data
            this.renderDashboard(data, accountId);
        } catch (error) {
            console.error('Error loading dashboard:', error);
            if (contentArea) {
                contentArea.innerHTML = '<div class="alert alert-danger">Error loading account data. Please refresh the page.</div>';
            }
        }
    }

    renderDashboard(data, accountId) {
        const contentArea = document.querySelector('.content-area');
        if (!contentArea) return;

        if (accountId === 'all') {
            // Render multi-account dashboard
            contentArea.innerHTML = `
                <h2>All Accounts Overview</h2>
                <div class="multi-account-view">
                    ${data.accounts.map(account => this.renderAccountCard(account)).join('')}
                </div>
                <div class="comparison-chart">
                    <h3>Performance Comparison</h3>
                    <canvas id="accountComparisonChart"></canvas>
                </div>
            `;
            
            // Initialize comparison chart
            this.initComparisonChart(data.accounts);
        } else {
            // Render single account dashboard
            const account = data.account;
            contentArea.innerHTML = `
                <h2>@${account.username} Dashboard</h2>
                <div class="row">
                    <div class="col-md-3">
                        <div class="card card-stat">
                            <div class="card-body">
                                <h5 class="card-title">Total Posts</h5>
                                <p class="card-text display-4">${account.total_posts}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card card-stat success">
                            <div class="card-body">
                                <h5 class="card-title">Successful</h5>
                                <p class="card-text display-4">${account.successful_posts}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card card-stat warning">
                            <div class="card-body">
                                <h5 class="card-title">Scheduled</h5>
                                <p class="card-text display-4">${account.scheduled_posts}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card card-stat danger">
                            <div class="card-body">
                                <h5 class="card-title">Failed</h5>
                                <p class="card-text display-4">${account.failed_posts}</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="recent-posts mt-4">
                    <h3>Recent Posts</h3>
                    ${this.renderRecentPosts(account.recent_posts)}
                </div>
            `;
        }
    }

    renderAccountCard(account) {
        return `
            <div class="account-card">
                <div class="account-card-header">
                    <div class="account-card-title">
                        <div class="account-avatar">${this.getAccountInitials(account.username)}</div>
                        <h5>@${account.username}</h5>
                    </div>
                    <div class="account-status ${account.is_active ? '' : 'inactive'}"></div>
                </div>
                <div class="account-metrics">
                    <div class="metric-item">
                        <div class="metric-value">${account.total_posts}</div>
                        <div class="metric-label">Posts</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${account.success_rate}%</div>
                        <div class="metric-label">Success</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${account.scheduled_posts}</div>
                        <div class="metric-label">Scheduled</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${account.failed_posts}</div>
                        <div class="metric-label">Failed</div>
                    </div>
                </div>
                <div class="mt-3">
                    <a href="/upload?account=${account.id}" class="btn btn-sm btn-primary">
                        <i class="fas fa-plus"></i> New Post
                    </a>
                    <a href="/accounts/${account.id}" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-cog"></i> Settings
                    </a>
                </div>
            </div>
        `;
    }

    renderRecentPosts(posts) {
        if (!posts || posts.length === 0) {
            return '<p class="text-muted">No recent posts</p>';
        }

        return `
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>Caption</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${posts.map(post => `
                            <tr>
                                <td>${new Date(post.scheduled_time).toLocaleString()}</td>
                                <td>${post.content_type}</td>
                                <td>${post.caption ? post.caption.substring(0, 50) + '...' : '-'}</td>
                                <td>
                                    <span class="badge bg-${this.getStatusColor(post.status)}">
                                        ${post.status}
                                    </span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    getStatusColor(status) {
        const colors = {
            'posted': 'success',
            'scheduled': 'warning',
            'failed': 'danger',
            'cancelled': 'secondary'
        };
        return colors[status] || 'primary';
    }

    initComparisonChart(accounts) {
        const ctx = document.getElementById('accountComparisonChart');
        if (!ctx) return;

        // This would integrate with Chart.js or another charting library
        // For now, just a placeholder
        console.log('Chart initialization for accounts:', accounts);
    }

    updateBulkOperationsUI() {
        const selectedCount = this.selectedAccounts.size;
        const bulkActions = document.getElementById('bulkActions');
        
        if (bulkActions) {
            if (selectedCount > 0) {
                bulkActions.style.display = 'block';
                bulkActions.querySelector('.selected-count').textContent = `${selectedCount} account${selectedCount > 1 ? 's' : ''} selected`;
            } else {
                bulkActions.style.display = 'none';
            }
        }

        // Update account selection UI
        document.querySelectorAll('.account-checkbox').forEach(checkbox => {
            const accountId = checkbox.querySelector('input').value;
            if (this.selectedAccounts.has(accountId)) {
                checkbox.classList.add('selected');
            } else {
                checkbox.classList.remove('selected');
            }
        });
    }

    async performBulkAction(action) {
        if (this.selectedAccounts.size === 0) {
            this.showToast('Please select at least one account', 'warning');
            return;
        }

        const accountIds = Array.from(this.selectedAccounts);
        
        try {
            const response = await fetch('/api/bulk-action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    account_ids: accountIds
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showToast(result.message, 'success');
                // Refresh the page or update UI
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showToast(result.message || 'Action failed', 'danger');
            }
        } catch (error) {
            console.error('Error performing bulk action:', error);
            this.showToast('Error performing action', 'danger');
        }
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
}

// Initialize account manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.accountManager = new AccountManager();
});

// Export for use in other scripts
window.AccountManager = AccountManager;
/**
 * 市场分析覆盖窗口组件 - 科幻风格
 * 
 * 功能：
 * - 从后端API获取市场分析数据
 * - 以科幻风格展示关键市场指标
 * - 支持显示/隐藏动画效果
 * - 响应式设计适配不同屏幕
 */
class MarketAnalysisOverlay {
    constructor(config = {}) {
        this.config = {
            backendUrl: 'http://localhost:8000',
            overlayId: 'market-analysis-overlay',
            contentId: 'market-analysis-content',
            autoHideDelay: 30000, // 30秒后自动隐藏
            ...config
        };
        
        this.isVisible = false;
        this.autoHideTimer = null;
        this.logger = null; // 日志记录器，由外部注入
    }

    /**
     * 初始化组件
     */
    initialize(logger = null) {
        this.logger = logger;
        this.createOverlayHTML();
        this.bindEvents();
        this.log('info', '📊 Market analysis overlay initialized');
    }

    /**
     * 创建覆盖窗口HTML结构
     */
    createOverlayHTML() {
        // 检查是否已存在
        if (document.getElementById(this.config.overlayId)) {
            return;
        }

        const overlayHTML = `
            <div id="${this.config.overlayId}" class="market-analysis-overlay hidden">
                <div class="market-analysis-header">
                    <div class="market-analysis-title">📊 Market Analysis</div>
                    <button class="market-analysis-close" id="market-analysis-close">×</button>
                </div>
                <div class="market-analysis-content" id="${this.config.contentId}">
                    <!-- 内容将通过JavaScript动态生成 -->
                </div>
            </div>
        `;

        // 将HTML添加到body
        document.body.insertAdjacentHTML('beforeend', overlayHTML);
    }

    /**
     * 绑定事件处理器
     */
    bindEvents() {
        const closeBtn = document.getElementById('market-analysis-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible) {
                this.hide();
            }
        });
    }

    /**
     * 从API获取并显示市场分析数据
     */
    async fetchAndDisplay() {
        try {
            this.log('info', '📊 Fetching market analysis data...');

            const response = await fetch(`${this.config.backendUrl}/analysis/market/basic`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const analysisResult = await response.json();

            this.log('success', '✅ Market analysis data retrieved');
            console.log('📊 Market Analysis Result:', analysisResult);

            // 显示分析结果
            this.displayAnalysis(analysisResult);

        } catch (error) {
            console.error('❌ Failed to fetch market analysis:', error);
            this.log('error', `Failed to get market analysis: ${error.message}`);
            
            // 显示错误信息
            this.displayError(error.message);
        }
    }

    /**
     * 显示市场分析窗口
     */
    displayAnalysis(analysisResult) {
        const overlay = document.getElementById(this.config.overlayId);
        const content = document.getElementById(this.config.contentId);
        
        if (!overlay || !content) {
            console.error('Market analysis overlay elements not found');
            return;
        }

        // 生成分析内容HTML
        const analysisHTML = this.generateAnalysisHTML(analysisResult);
        content.innerHTML = analysisHTML;

        // 显示窗口
        this.show();
        
        this.log('info', '📊 Market analysis window displayed');
    }

    /**
     * 显示错误信息
     */
    displayError(errorMessage) {
        const overlay = document.getElementById(this.config.overlayId);
        const content = document.getElementById(this.config.contentId);
        
        if (!overlay || !content) {
            return;
        }

        content.innerHTML = `
            <div class="market-metric-group">
                <div class="metric-group-title">❌ Error</div>
                <div class="metric-item">
                    <span class="metric-label" style="color: #ef4444;">${errorMessage}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Please try again later</span>
                </div>
            </div>
        `;

        this.show();
    }

    /**
     * 生成分析HTML内容
     */
    generateAnalysisHTML(data) {
        const { 
            tenant_metrics, 
            property_metrics, 
            supply_demand, 
            price_metrics, 
            market_health_indicator,
            api_metadata 
        } = data;

        if (!tenant_metrics || !property_metrics) {
            return '<div class="market-metric-group"><div class="metric-group-title">❌ Invalid Data</div></div>';
        }

        return `
            <!-- 租户指标 -->
            <div class="market-metric-group">
                <div class="metric-group-title">🏠 Rental Market</div>
                <div class="metric-item">
                    <span class="metric-label">Total Tenants:</span>
                    <span class="metric-value">${tenant_metrics.total_tenants || 0}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Rental Rate:</span>
                    <span class="metric-value ${(tenant_metrics.rental_rate_percentage || 0) < 50 ? 'warning' : ''}">${tenant_metrics.rental_rate_percentage || 0}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Avg Budget:</span>
                    <span class="metric-value">£${tenant_metrics.average_budget || 0}</span>
                </div>
            </div>

            <!-- 房产指标 -->
            <div class="market-metric-group">
                <div class="metric-group-title">🏢 Property Market</div>
                <div class="metric-item">
                    <span class="metric-label">Available:</span>
                    <span class="metric-value">${property_metrics.available_properties || 0}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Occupancy Rate:</span>
                    <span class="metric-value ${(property_metrics.occupancy_rate_percentage || 0) < 50 ? 'warning' : ''}">${property_metrics.occupancy_rate_percentage || 0}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Avg Rent:</span>
                    <span class="metric-value">£${property_metrics.average_rent ? property_metrics.average_rent.toFixed(0) : 0}</span>
                </div>
            </div>

            ${supply_demand ? `
            <!-- 供需关系 -->
            <div class="market-metric-group">
                <div class="metric-group-title">⚖️ Supply & Demand</div>
                <div class="metric-item">
                    <span class="metric-label">Market Type:</span>
                    <span class="metric-value ${supply_demand.market_condition === "Buyer's Market" ? 'warning' : ''}">${supply_demand.market_condition || 'Unknown'}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">S/D Ratio:</span>
                    <span class="metric-value">${supply_demand.supply_demand_ratio ? supply_demand.supply_demand_ratio.toFixed(1) : 'N/A'}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Tension:</span>
                    <span class="metric-value ${supply_demand.market_tension === 'Low' ? 'warning' : ''}">${supply_demand.market_tension || 'Unknown'}</span>
                </div>
            </div>
            ` : ''}

            ${price_metrics && price_metrics.price_ranges ? `
            <!-- 价格区间 -->
            <div class="market-metric-group">
                <div class="metric-group-title">💰 Price Ranges</div>
                <div class="metric-item">
                    <span class="metric-label">< £1,000:</span>
                    <span class="metric-value">${price_metrics.price_ranges.under_1000 || 0}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">£1K - £2K:</span>
                    <span class="metric-value">${(price_metrics.price_ranges['1000_1500'] || 0) + (price_metrics.price_ranges['1500_2000'] || 0)}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">> £3,000:</span>
                    <span class="metric-value">${price_metrics.price_ranges.over_3000 || 0}</span>
                </div>
            </div>
            ` : ''}

            ${market_health_indicator ? `
            <!-- 市场健康指标 -->
            <div class="market-health-indicator">
                <div class="health-score ${(market_health_indicator.health_score || 0) < 30 ? 'danger' : (market_health_indicator.health_score || 0) < 60 ? 'warning' : ''}">${market_health_indicator.health_score ? market_health_indicator.health_score.toFixed(1) : 'N/A'}</div>
                <div class="health-status">${market_health_indicator.health_status || 'Unknown'}</div>
            </div>
            ` : ''}

            <!-- 时间戳 -->
            <div class="analysis-timestamp">
                Updated: ${api_metadata && api_metadata.response_time ? new Date(api_metadata.response_time).toLocaleTimeString() : new Date().toLocaleTimeString()}
            </div>
        `;
    }

    /**
     * 显示窗口
     */
    show() {
        const overlay = document.getElementById(this.config.overlayId);
        if (overlay) {
            overlay.classList.remove('hidden');
            overlay.classList.add('show');
            this.isVisible = true;

            // 设置自动隐藏定时器
            this.setAutoHideTimer();
        }
    }

    /**
     * 隐藏窗口
     */
    hide() {
        const overlay = document.getElementById(this.config.overlayId);
        if (overlay) {
            overlay.classList.add('hidden');
            overlay.classList.remove('show');
            this.isVisible = false;

            // 清除自动隐藏定时器
            this.clearAutoHideTimer();
        }
    }

    /**
     * 设置自动隐藏定时器
     */
    setAutoHideTimer() {
        this.clearAutoHideTimer();
        if (this.config.autoHideDelay > 0) {
            this.autoHideTimer = setTimeout(() => {
                this.hide();
                this.log('info', '📊 Market analysis window auto-hidden');
            }, this.config.autoHideDelay);
        }
    }

    /**
     * 清除自动隐藏定时器
     */
    clearAutoHideTimer() {
        if (this.autoHideTimer) {
            clearTimeout(this.autoHideTimer);
            this.autoHideTimer = null;
        }
    }

    /**
     * 切换显示状态
     */
    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.fetchAndDisplay();
        }
    }

    /**
     * 日志记录
     */
    log(type, message) {
        if (this.logger && typeof this.logger.addLog === 'function') {
            this.logger.addLog(type, message);
        } else {
            console.log(`[MarketAnalysis] ${type}: ${message}`);
        }
    }

    /**
     * 销毁组件
     */
    destroy() {
        this.clearAutoHideTimer();
        const overlay = document.getElementById(this.config.overlayId);
        if (overlay) {
            overlay.remove();
        }
        this.isVisible = false;
    }
}

export default MarketAnalysisOverlay;
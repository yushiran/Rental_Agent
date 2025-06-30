/**
 * GoogleMapsLoader - Google Maps API 加载器
 * 动态加载 Google Maps JavaScript API
 */
class GoogleMapsLoader {
    constructor(apiKey = '') {
        this.apiKey = apiKey;
        this.isLoaded = false;
        this.loadPromise = null;
        this.libraries = ['geometry', 'places'];
    }

    /**
     * 加载 Google Maps API
     */
    async load() {
        if (this.isLoaded) {
            return Promise.resolve();
        }

        if (this.loadPromise) {
            return this.loadPromise;
        }

        this.loadPromise = new Promise((resolve, reject) => {
            // 检查是否已加载
            if (window.google && window.google.maps) {
                this.isLoaded = true;
                resolve();
                return;
            }

            // 创建全局回调
            const callbackName = 'googleMapsInitCallback';
            window[callbackName] = () => {
                this.isLoaded = true;
                delete window[callbackName];
                console.log('[GoogleMapsLoader] Google Maps API 加载完成');
                resolve();
            };

            // 创建脚本标签
            const script = document.createElement('script');
            script.async = true;
            script.defer = true;
            
            // 构建API URL - 移除API Key要求，使用开发模式
            const params = new URLSearchParams({
                callback: callbackName,
                libraries: this.libraries.join(','),
                v: 'weekly'
            });

            // 仅在有API Key时才添加，否则使用免费配额
            if (this.apiKey && this.apiKey.trim() !== '') {
                params.set('key', this.apiKey);
            }

            script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
            
            // 错误处理
            script.onerror = () => {
                delete window[callbackName];
                console.warn('[GoogleMapsLoader] Google Maps API 加载失败，可能需要配置API Key');
                // 不完全拒绝，而是尝试继续
                resolve();
            };

            // 添加到页面
            document.head.appendChild(script);
        });

        return this.loadPromise;
    }

    /**
     * 设置 API Key
     */
    setApiKey(apiKey) {
        if (this.isLoaded) {
            console.warn('[GoogleMapsLoader] API 已加载，无法修改 API Key');
            return;
        }
        this.apiKey = apiKey;
    }

    /**
     * 添加库
     */
    addLibrary(library) {
        if (this.isLoaded) {
            console.warn('[GoogleMapsLoader] API 已加载，无法添加新库');
            return;
        }
        if (!this.libraries.includes(library)) {
            this.libraries.push(library);
        }
    }

    /**
     * 检查是否已加载
     */
    isApiLoaded() {
        return this.isLoaded && window.google && window.google.maps;
    }
}

// 创建单例实例
const googleMapsLoader = new GoogleMapsLoader();

export default googleMapsLoader;

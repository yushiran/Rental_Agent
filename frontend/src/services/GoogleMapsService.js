/**
 * Google Maps Static API Service
 * 用于生成带有标记的静态地图图像
 */
export default class GoogleMapsService {
  constructor() {
    this.apiKey = null;
    this.baseUrl = 'https://maps.googleapis.com/maps/api/staticmap';
    this.configLoaded = false;
  }

  /**
   * 从后端获取API密钥
   */
  async loadConfig() {
    if (this.configLoaded && this.apiKey) {
      return this.apiKey;
    }

    try {
      const response = await fetch('http://localhost:8000/config');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const config = await response.json();
      this.apiKey = config.google_maps_api_key;
      this.configLoaded = true;
      console.log('Google Maps API key loaded from backend:', this.apiKey);
      return this.apiKey;
    } catch (error) {
      console.error('Failed to load Google Maps API key from backend:', error);
      // 使用备用密钥
      this.apiKey = 'AIzaSyDSflr_l6w6IZIhqcFO2J_0WJacRga2UiU';
      this.configLoaded = true;
      console.log('Using fallback API key:', this.apiKey);
      return this.apiKey;
    }
  }

  /**
   * 构建Google Static Map URL
   * @param {Object} options - 地图选项
   * @param {Array} markers - 标记数组
   * @returns {string} 地图URL
   */
  async buildMapUrl(options = {}, markers = []) {
    // 确保API密钥已加载
    await this.loadConfig();
    
    const params = [];
    
    // 基本参数
    params.push(`size=${options.size || '800x600'}`);
    params.push(`zoom=${options.zoom || 12}`);
    params.push(`maptype=${options.maptype || 'roadmap'}`);
    
    // 地图中心
    if (options.center) {
      params.push(`center=${options.center}`);
    } else {
      // 默认中心为伦敦
      params.push('center=51.5074,-0.1278');
    }
    
    // 地图样式
    if (options.style) {
      params.push(`style=${options.style}`);
    }
    
    // 添加标记
    markers.forEach(marker => {
      const markerParams = [];
      
      if (marker.color) markerParams.push(`color:${marker.color}`);
      if (marker.size) markerParams.push(`size:${marker.size}`);
      if (marker.label) markerParams.push(`label:${marker.label}`);
      if (marker.icon) markerParams.push(`icon:${marker.icon}`);
      
      markerParams.push(`${marker.lat},${marker.lng}`);
      
      params.push(`markers=${markerParams.join('|')}`);
    });
    
    // API密钥
    params.push(`key=${this.apiKey}`);
    
    return `${this.baseUrl}?${params.join('&')}`;
  }

  /**
   * 为房产数据创建地图URL
   * @param {Array} properties - 房产数据数组
   * @param {Object} options - 地图选项
   * @returns {Promise<string>} 地图URL
   */
  async createPropertyMap(properties, options = {}) {
    const markers = properties.map((property, index) => ({
      lat: property.latitude,
      lng: property.longitude,
      color: 'red',
      size: 'small',
      label: String.fromCharCode(65 + (index % 26)) // A, B, C, ...
    }));
    
    // 计算地图边界以包含所有标记
    if (properties.length > 0) {
      const lats = properties.map(p => p.latitude);
      const lngs = properties.map(p => p.longitude);
      
      const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2;
      const centerLng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
      
      options.center = `${centerLat},${centerLng}`;
    }
    
    return await this.buildMapUrl({
      size: '800x600',
      zoom: 11,
      maptype: 'roadmap',
      ...options
    }, markers);
  }

  /**
   * 创建伦敦中心地图
   * @param {Object} options - 地图选项
   * @returns {Promise<string>} 地图URL
   */
  async createLondonMap(options = {}) {
    return await this.buildMapUrl({
      size: '800x600',
      zoom: 11,
      maptype: 'roadmap',
      center: '51.5074,-0.1278', // 伦敦中心
      ...options
    });
  }

  /**
   * 将经纬度转换为屏幕坐标
   * @param {number} lat - 纬度
   * @param {number} lng - 经度
   * @param {Object} bounds - 地图边界
   * @param {number} width - 地图宽度
   * @param {number} height - 地图高度
   * @returns {Object} {x, y} 屏幕坐标
   */
  latLngToScreenCoordinates(lat, lng, bounds, width = 800, height = 600) {
    const x = ((lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * width;
    const y = ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * height;
    
    return {
      x: Math.max(0, Math.min(x, width)),
      y: Math.max(0, Math.min(y, height))
    };
  }

  /**
   * 获取伦敦的标准边界
   * @returns {Object} 伦敦边界坐标
   */
  getLondonBounds() {
    return {
      minLat: 51.28,
      maxLat: 51.69,
      minLng: -0.51,
      maxLng: 0.33
    };
  }
}
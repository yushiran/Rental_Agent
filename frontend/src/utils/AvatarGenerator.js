import { createAvatar } from '@dicebear/core';
import { pixelArt } from '@dicebear/collection';

/**
 * AvatarGenerator - 头像生成器
 * 使用 DiceBear pixelArt 风格为租客和房东生成个性化头像
 */
class AvatarGenerator {
    constructor() {
        // 头像缓存
        this.avatarCache = new Map();
    }

    /**
     * 为租客生成头像 - 年轻活泼风格
     */
    generateTenantAvatar(agentId, name = '') {
        // 使用缓存避免重复生成
        const cacheKey = `tenant_${agentId}`;
        if (this.avatarCache.has(cacheKey)) {
            return this.avatarCache.get(cacheKey);
        }

        const avatar = createAvatar(pixelArt, {
            seed: name || agentId, // 使用名字作为种子
            size: 32, // 地图标记合适的大小
            // 租客使用明亮活泼的背景色
            backgroundColor: ['b6e3f4', 'c0aede', 'd1d4f9', 'ffd5dc', 'ffdfbf'],
            backgroundType: ['solid'],
            
            // 服装 - 休闲风格
            clothing: ['variant01', 'variant02', 'variant03', 'variant05', 'variant08', 'variant12'],
            clothingColor: ['5bc0de', '44c585', '88d8b0', '428bca', 'ffc425', 'ffd969'],
            
            // 发型 - 多样化
            hair: ['short01', 'short02', 'short03', 'short05', 'long01', 'long02', 'long05'],
            hairColor: ['603a14', '611c17', '83623b', '603015', 'a78961', 'cab188'],
            
            // 表情 - 开心为主
            mouth: ['happy01', 'happy02', 'happy03', 'happy05', 'happy08', 'happy11'],
            mouthColor: ['c98276', 'd29985', 'e35d6a'],
            
            // 眼睛
            eyes: ['variant01', 'variant02', 'variant04', 'variant06', 'variant08'],
            eyesColor: ['5b7c8b', '647b90', '588387'],
            
            // 肤色
            skinColor: ['cb9e6e', 'e0b687', 'eac393', 'f5cfa0', 'ffdbac'],
            
            // 配饰 - 较少概率
            accessoriesProbability: 20,
            accessories: ['variant01', 'variant03'],
            accessoriesColor: ['d3d3d3', 'ffd700'],
            
            // 眼镜 - 很少概率
            glassesProbability: 10,
            glasses: ['light01', 'light02', 'light03'],
            glassesColor: ['4b4b4b', '5f705c'],
            
            // 帽子 - 很少概率  
            hatProbability: 15,
            hat: ['variant02', 'variant05', 'variant08'],
            hatColor: ['3d8a6b', '2663a3', 'cc6192']
        });

        const dataUri = avatar.toDataUri();
        this.avatarCache.set(cacheKey, dataUri);
        return dataUri;
    }

    /**
     * 为房东生成头像 - 商务专业风格，都戴帽子和眼镜
     */
    generateLandlordAvatar(agentId, name = '') {
        // 使用缓存避免重复生成
        const cacheKey = `landlord_${agentId}`;
        if (this.avatarCache.has(cacheKey)) {
            return this.avatarCache.get(cacheKey);
        }

        const avatar = createAvatar(pixelArt, {
            seed: name || agentId, // 使用名字作为种子
            size: 32, // 地图标记合适的大小
            // 房东使用深色商务风格的背景色
            backgroundColor: ['264653', '2a9d8f', 'e9c46a', 'f4a261', 'e76f51'],
            backgroundType: ['solid'],
            
            // 服装 - 正式商务风格
            clothing: ['variant04', 'variant06', 'variant07', 'variant09', 'variant13', 'variant16'],
            clothingColor: ['03396c', '428bca', '00b159', 'ae0001', 'd11141'],
            
            // 发型 - 成熟稳重
            hair: ['short04', 'short06', 'short08', 'short12', 'short15', 'short18'],
            hairColor: ['28150a', '603015', '612616', '83623b'],
            
            // 表情 - 严肃或中性
            mouth: ['happy04', 'happy07', 'happy10', 'sad03', 'sad05'],
            mouthColor: ['c98276', 'd29985'],
            
            // 眼睛
            eyes: ['variant03', 'variant05', 'variant07', 'variant09', 'variant11'],
            eyesColor: ['5b7c8b', '76778b', '876658'],
            
            // 肤色 - 偏向成熟
            skinColor: ['8d5524', 'a26d3d', 'b68655', 'cb9e6e'],
            
            // 胡子 - 较高概率
            beardProbability: 60,
            beard: ['variant01', 'variant02', 'variant04', 'variant06'],
            
            // 配饰 - 低概率
            accessoriesProbability: 30,
            accessories: ['variant02', 'variant04'],
            accessoriesColor: ['a9a9a9', 'daa520'],
            
            // 眼镜 - 高概率，房东都戴眼镜显专业
            glassesProbability: 85,
            glasses: ['dark01', 'dark02', 'dark03', 'dark05', 'light04', 'light06'],
            glassesColor: ['191919', '323232', '4b4b4b', '43677d'],
            
            // 帽子 - 高概率，房东都戴帽子显权威
            hatProbability: 80,
            hat: ['variant01', 'variant03', 'variant04', 'variant06', 'variant07'],
            hatColor: ['2e1e05', '614f8a', '2663a3', '989789', 'a62116']
        });

        const dataUri = avatar.toDataUri();
        this.avatarCache.set(cacheKey, dataUri);
        return dataUri;
    }

    /**
     * 根据智能体类型生成头像
     */
    async generateAvatar(agentId, type, name = '') {
        try {
            switch (type) {
                case 'tenant':
                    return await this.generateTenantAvatar(agentId, name);
                case 'landlord':
                    return await this.generateLandlordAvatar(agentId, name);
                default:
                    console.warn(`[AvatarGenerator] 未知的智能体类型: ${type}`);
                    return await this.generateTenantAvatar(agentId, name);
            }
        } catch (error) {
            console.error(`[AvatarGenerator] 生成头像失败:`, error);
            // 返回 null，让系统使用后备图标
            return null;
        }
    }

    /**
     * 批量生成头像
     */
    async generateAvatarsForAgents(agents) {
        const avatars = new Map();
        
        for (const agent of agents) {
            const avatar = await this.generateAvatar(agent.id, agent.type, agent.name);
            if (avatar) {
                avatars.set(agent.id, avatar);
            }
        }
        
        console.log(`[AvatarGenerator] 批量生成了 ${avatars.size} 个头像`);
        return avatars;
    }

    /**
     * 清除头像缓存
     */
    clearCache() {
        this.avatarCache.clear();
        console.log('[AvatarGenerator] 缓存已清除');
    }

    /**
     * 获取缓存的头像
     */
    getCachedAvatar(agentId, type) {
        const cacheKey = `${type}_${agentId}`;
        return this.avatarCache.get(cacheKey);
    }
}

export default AvatarGenerator;

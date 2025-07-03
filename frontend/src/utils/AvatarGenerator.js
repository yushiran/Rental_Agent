import { createAvatar } from '@dicebear/core';
import { pixelArt } from '@dicebear/collection';

/**
 * AvatarGenerator - Avatar Generator
 * Uses DiceBear pixelArt style to create personalized avatars for tenants and landlords
 */
class AvatarGenerator {
    constructor() {
        // Avatar cache
        this.avatarCache = new Map();
    }

    /**
     * Generate avatar for tenant - young and lively style
     */
    generateTenantAvatar(agentId, name = '') {
        // Use cache to avoid regenerating
        const cacheKey = `tenant_${agentId}`;
        if (this.avatarCache.has(cacheKey)) {
            return this.avatarCache.get(cacheKey);
        }

        const avatar = createAvatar(pixelArt, {
            seed: name || agentId, // Use name as seed
            size: 32, // Appropriate size for map markers
            // Tenants use bright, lively background colors
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
     * Generate avatar for landlord - professional business style with hats and glasses
     */
    generateLandlordAvatar(agentId, name = '') {
        // Use cache to avoid regenerating
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
            
            // Clothing - formal business style
            clothing: ['variant04', 'variant06', 'variant07', 'variant09', 'variant13', 'variant16'],
            clothingColor: ['03396c', '428bca', '00b159', 'ae0001', 'd11141'],
            
            // Hair - mature and professional
            hair: ['short04', 'short06', 'short08', 'short12', 'short15', 'short18'],
            hairColor: ['28150a', '603015', '612616', '83623b'],
            
            // Expression - serious or neutral
            mouth: ['happy04', 'happy07', 'happy10', 'sad03', 'sad05'],
            mouthColor: ['c98276', 'd29985'],
            
            // Eyes
            eyes: ['variant03', 'variant05', 'variant07', 'variant09', 'variant11'],
            eyesColor: ['5b7c8b', '76778b', '876658'],
            
            // Skin color - more mature tones
            skinColor: ['8d5524', 'a26d3d', 'b68655', 'cb9e6e'],
            
            // Beard - high probability
            beardProbability: 60,
            beard: ['variant01', 'variant02', 'variant04', 'variant06'],
            
            // Accessories - low probability
            accessoriesProbability: 30,
            accessories: ['variant02', 'variant04'],
            accessoriesColor: ['a9a9a9', 'daa520'],
            
            // Glasses - high probability for professional look
            glassesProbability: 85,
            glasses: ['dark01', 'dark02', 'dark03', 'dark05', 'light04', 'light06'],
            glassesColor: ['191919', '323232', '4b4b4b', '43677d'],
            
            // Hat - high probability for authoritative look
            hatProbability: 80,
            hat: ['variant01', 'variant03', 'variant04', 'variant06', 'variant07'],
            hatColor: ['2e1e05', '614f8a', '2663a3', '989789', 'a62116']
        });

        const dataUri = avatar.toDataUri();
        this.avatarCache.set(cacheKey, dataUri);
        return dataUri;
    }

    /**
     * Generate avatar based on agent type
     */
    async generateAvatar(agentId, type, name = '') {
        try {
            switch (type) {
                case 'tenant':
                    return await this.generateTenantAvatar(agentId, name);
                case 'landlord':
                    return await this.generateLandlordAvatar(agentId, name);
                default:
                    console.warn(`[AvatarGenerator] Unknown agent type: ${type}`);
                    return await this.generateTenantAvatar(agentId, name);
            }
        } catch (error) {
            console.error(`[AvatarGenerator] Failed to generate avatar:`, error);
            // Return null to let system use fallback icon
            return null;
        }
    }

    /**
     * Generate avatars in batch for multiple agents
     */
    async generateAvatarsForAgents(agents) {
        const avatars = new Map();
        
        for (const agent of agents) {
            const avatar = await this.generateAvatar(agent.id, agent.type, agent.name);
            if (avatar) {
                avatars.set(agent.id, avatar);
            }
        }
        
        console.log(`[AvatarGenerator] Generated ${avatars.size} avatars in batch`);
        return avatars;
    }

    /**
     * Clear avatar cache
     */
    clearCache() {
        this.avatarCache.clear();
        console.log('[AvatarGenerator] Cache cleared');
    }

    /**
     * Get cached avatar
     */
    getCachedAvatar(agentId, type) {
        const cacheKey = `${type}_${agentId}`;
        return this.avatarCache.get(cacheKey);
    }
}

export default AvatarGenerator;

import { Character } from './Tenant';

/**
 * Landlord character class
 */
export default class Landlord extends Character {
  constructor(scene, x, y, characterName = 'aristotle') {
    super(scene, x, y, characterName);
    this.type = 'landlord';
    
    // Set appropriate scale for the character
    this.sprite.setScale(1.5);
  }
}

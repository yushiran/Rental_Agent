import { Character } from './Tenant';

/**
 * Landlord character class
 */
export default class Landlord extends Character {
  constructor(scene, x, y) {
    super(scene, x, y, 'landlord', 0);
    this.type = 'landlord';
    this.id = null; // Used to track which landlord this is
    
    // Set the scale if needed
    this.sprite.setScale(2);
  }
  
  /**
   * Set the landlord's ID (used to identify which landlord is being addressed)
   */
  setId(id) {
    this.id = id;
    return this;
  }
}

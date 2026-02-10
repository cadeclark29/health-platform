// Storage Service - Persistent storage using AsyncStorage

import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  USER_ID: '@health_platform:user_id',
  USER_DATA: '@health_platform:user_data',
  SUPPLEMENT_TIMINGS: '@health_platform:supplement_timings',
  SUPPLEMENT_DOSES: '@health_platform:supplement_doses',
};

class StorageService {
  // User ID
  async getUserId(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(KEYS.USER_ID);
    } catch (error) {
      console.error('Error getting user ID:', error);
      return null;
    }
  }

  async setUserId(userId: string): Promise<void> {
    try {
      await AsyncStorage.setItem(KEYS.USER_ID, userId);
    } catch (error) {
      console.error('Error setting user ID:', error);
    }
  }

  async removeUserId(): Promise<void> {
    try {
      await AsyncStorage.removeItem(KEYS.USER_ID);
    } catch (error) {
      console.error('Error removing user ID:', error);
    }
  }

  // User Data (cached)
  async getUserData<T>(): Promise<T | null> {
    try {
      const data = await AsyncStorage.getItem(KEYS.USER_DATA);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error getting user data:', error);
      return null;
    }
  }

  async setUserData<T>(data: T): Promise<void> {
    try {
      await AsyncStorage.setItem(KEYS.USER_DATA, JSON.stringify(data));
    } catch (error) {
      console.error('Error setting user data:', error);
    }
  }

  // Supplement Timings (user overrides via drag-drop)
  async getSupplementTimings(): Promise<Record<string, string>> {
    try {
      const data = await AsyncStorage.getItem(KEYS.SUPPLEMENT_TIMINGS);
      return data ? JSON.parse(data) : {};
    } catch (error) {
      console.error('Error getting supplement timings:', error);
      return {};
    }
  }

  async setSupplementTiming(supplementId: string, timeSlot: string): Promise<void> {
    try {
      const timings = await this.getSupplementTimings();
      timings[supplementId] = timeSlot;
      await AsyncStorage.setItem(KEYS.SUPPLEMENT_TIMINGS, JSON.stringify(timings));
    } catch (error) {
      console.error('Error setting supplement timing:', error);
    }
  }

  async setSupplementTimings(timings: Record<string, string>): Promise<void> {
    try {
      await AsyncStorage.setItem(KEYS.SUPPLEMENT_TIMINGS, JSON.stringify(timings));
    } catch (error) {
      console.error('Error setting supplement timings:', error);
    }
  }

  // Supplement Doses (user overrides)
  async getSupplementDoses(): Promise<Record<string, string>> {
    try {
      const data = await AsyncStorage.getItem(KEYS.SUPPLEMENT_DOSES);
      return data ? JSON.parse(data) : {};
    } catch (error) {
      console.error('Error getting supplement doses:', error);
      return {};
    }
  }

  async setSupplementDose(supplementId: string, dose: string): Promise<void> {
    try {
      const doses = await this.getSupplementDoses();
      doses[supplementId] = dose;
      await AsyncStorage.setItem(KEYS.SUPPLEMENT_DOSES, JSON.stringify(doses));
    } catch (error) {
      console.error('Error setting supplement dose:', error);
    }
  }

  async setSupplementDoses(doses: Record<string, string>): Promise<void> {
    try {
      await AsyncStorage.setItem(KEYS.SUPPLEMENT_DOSES, JSON.stringify(doses));
    } catch (error) {
      console.error('Error setting supplement doses:', error);
    }
  }

  // Clear all data (logout)
  async clearAll(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([
        KEYS.USER_ID,
        KEYS.USER_DATA,
        KEYS.SUPPLEMENT_TIMINGS,
        KEYS.SUPPLEMENT_DOSES,
      ]);
    } catch (error) {
      console.error('Error clearing storage:', error);
    }
  }
}

export const storage = new StorageService();

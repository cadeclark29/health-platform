// App State Hook - Global state management using React Context

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  User,
  AnalyticsData,
  HealthData,
  Supplement,
  SupplementLog,
  LifeEvent,
  TimeSlot,
  StackSupplement,
  InsightsData,
  HealthAlert,
} from '../types';
import { api } from '../services/api';
import { storage } from '../services/storage';

// Supplement timing defaults
const SUPPLEMENT_TIMING: Record<string, TimeSlot> = {
  // Morning supplements
  vitamin_d3: 'morning',
  vitamin_d: 'morning',
  fish_oil: 'morning',
  omega_3: 'morning',
  vitamin_b12: 'morning',
  vitamin_b_complex: 'morning',
  iron: 'morning',
  coq10: 'morning',
  rhodiola: 'morning',
  cordyceps: 'morning',
  lions_mane: 'morning',
  caffeine: 'morning',

  // Intra-day supplements
  creatine: 'intraday',
  alpha_lipoic_acid: 'intraday',
  electrolytes: 'intraday',

  // Evening supplements
  magnesium_glycinate: 'evening',
  magnesium: 'evening',
  glycine: 'evening',
  melatonin: 'evening',
  l_theanine: 'evening',
  ashwagandha: 'evening',
  valerian: 'evening',
  gaba: 'evening',
  zinc: 'evening',
  apigenin: 'evening',
  magnesium_l_threonate: 'evening',
};

interface AppState {
  // Auth state
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  userId: string | null;

  // Data state
  analyticsData: AnalyticsData | null;
  insightsData: InsightsData | null;
  selectedDate: Date;
  ouraConnected: boolean;
  healthAlerts: HealthAlert[];

  // Actions
  signIn: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  setSelectedDate: (date: Date) => void;
  refreshData: () => Promise<void>;
  syncOura: () => Promise<void>;
  logSupplement: (supplementId: string) => Promise<void>;
  unlogSupplement: (logId: string) => Promise<void>;
  updateUser: (updates: Partial<User>) => Promise<void>;

  // Supplement management
  updateSupplementTiming: (supplementId: string, timeSlot: TimeSlot) => Promise<void>;
  updateSupplementDose: (supplementId: string, dosage: string) => Promise<void>;
  addSupplement: (data: { supplement_id: string; supplement_name: string; dosage: string; timeSlot: TimeSlot }) => Promise<void>;
  removeSupplement: (supplementStartId: string) => Promise<void>;

  // Life events
  addLifeEvent: (data: { event_type: string; event_date: string; description?: string }) => Promise<void>;
  deleteLifeEvent: (eventId: string) => Promise<void>;

  // Oura management
  disconnectOura: () => Promise<void>;
  resetAccount: () => Promise<void>;
  completeOnboarding: () => Promise<void>;

  // Computed
  getHealthDataForDate: (date: Date) => HealthData | undefined;
  getStackSupplements: () => { morning: StackSupplement[]; intraday: StackSupplement[]; evening: StackSupplement[] };
  getTodaysLogs: () => Record<string, SupplementLog>;
  getExistingSupplementIds: () => string[];
  getDateString: (date: Date) => string;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [insightsData, setInsightsData] = useState<InsightsData | null>(null);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [ouraConnected, setOuraConnected] = useState(false);
  const [userTimings, setUserTimings] = useState<Record<string, string>>({});
  const [userDoses, setUserDoses] = useState<Record<string, string>>({});
  const [healthAlerts, setHealthAlerts] = useState<HealthAlert[]>([]);

  // Initialize on mount
  useEffect(() => {
    initializeApp();
  }, []);

  // Generate alerts when health data or selected date changes
  useEffect(() => {
    if (analyticsData) {
      const alerts = generateHealthAlerts(analyticsData, selectedDate);
      setHealthAlerts(alerts);
    }
  }, [analyticsData, selectedDate]);

  const initializeApp = async () => {
    try {
      const storedUserId = await storage.getUserId();
      if (storedUserId) {
        setUserId(storedUserId);
        const userData = await api.getUser(storedUserId);
        setUser(userData);
        await loadData(storedUserId);
      }
    } catch (error) {
      console.error('Error initializing app:', error);
      await storage.removeUserId();
    } finally {
      setIsLoading(false);
    }
  };

  const loadData = async (uid: string) => {
    try {
      const [data, timings, doses] = await Promise.all([
        api.getAnalytics(uid, 60),
        storage.getSupplementTimings(),
        storage.getSupplementDoses(),
      ]);
      setAnalyticsData(data);
      setUserTimings(timings);
      setUserDoses(doses);

      // Check Oura connection status via API, fall back to data check
      api.getOuraStatus(uid)
        .then(status => setOuraConnected(status?.connected === true))
        .catch(() => {
          const hasOuraData = data.health_data?.some(h => h.source === 'oura');
          setOuraConnected(hasOuraData);
        });

      // Load insights in background (non-blocking)
      api.getSupplementInsights(uid)
        .then(insights => setInsightsData(insights))
        .catch(() => {}); // Silently fail - insights are optional
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const signIn = async (email: string) => {
    setIsLoading(true);
    try {
      const userData = await api.signIn(email);
      setUser(userData);
      setUserId(userData.id);
      await storage.setUserId(userData.id);
      await loadData(userData.id);
    } finally {
      setIsLoading(false);
    }
  };

  const signOut = async () => {
    await storage.clearAll();
    setUser(null);
    setUserId(null);
    setAnalyticsData(null);
    setInsightsData(null);
    setOuraConnected(false);
    setHealthAlerts([]);
  };

  const refreshData = useCallback(async () => {
    if (userId) {
      await loadData(userId);
    }
  }, [userId]);

  const syncOura = async () => {
    if (!userId) return;
    try {
      await api.syncOuraHistory(userId, 7);
      await refreshData();
    } catch (error) {
      console.error('Error syncing Oura:', error);
    }
  };

  const getDateString = (date: Date): string => {
    // Use local date, not UTC (toISOString uses UTC which can be wrong day)
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const getHealthDataForDate = (date: Date): HealthData | undefined => {
    const dateStr = getDateString(date);
    return analyticsData?.health_data?.find(h => h.date === dateStr);
  };

  const getTodaysLogs = (): Record<string, SupplementLog> => {
    const dateStr = getDateString(selectedDate);
    const allLogs = analyticsData?.supplement_logs || [];

    const logs: Record<string, SupplementLog> = {};
    allLogs
      .filter(l => l.date === dateStr)  // API uses "date" not "log_date"
      .forEach(l => {
        const normalizedId = l.supplement_id?.toLowerCase().replace(/-/g, '_');
        if (normalizedId) {
          logs[normalizedId] = l;
        }
      });
    return logs;
  };

  const getStackSupplements = () => {
    const supplements = analyticsData?.supplement_starts?.filter(s => !s.end_date) || [];
    const logs = getTodaysLogs();

    const groups: { morning: StackSupplement[]; intraday: StackSupplement[]; evening: StackSupplement[] } = {
      morning: [],
      intraday: [],
      evening: [],
    };

    supplements.forEach(supp => {
      const suppId = supp.supplement_id?.toLowerCase().replace(/-/g, '_');
      const timing: TimeSlot = (userTimings[suppId] as TimeSlot) ||
                               SUPPLEMENT_TIMING[suppId] ||
                               'morning';
      const isTaken = !!logs[suppId];
      const displayDose = userDoses[suppId] || supp.dosage;

      const stackSupp: StackSupplement = {
        ...supp,
        timeSlot: timing,
        isTaken,
        displayDose,
      };

      groups[timing].push(stackSupp);
    });

    return groups;
  };

  const logSupplement = async (supplementId: string) => {
    if (!userId) {
      throw new Error('Not logged in');
    }
    const dateStr = getDateString(selectedDate);
    await api.logSupplement(userId, supplementId, dateStr);
    await refreshData();
  };

  const unlogSupplement = async (logId: string) => {
    if (!userId) {
      throw new Error('Not logged in');
    }
    await api.deleteSupplementLog(userId, logId);
    await refreshData();
  };

  const updateSupplementTiming = async (supplementId: string, timeSlot: TimeSlot) => {
    const newTimings = { ...userTimings, [supplementId]: timeSlot };
    setUserTimings(newTimings);
    await storage.setSupplementTimings(newTimings);
  };

  const updateSupplementDose = async (supplementId: string, dosage: string) => {
    const newDoses = { ...userDoses, [supplementId]: dosage };
    setUserDoses(newDoses);
    await storage.setSupplementDoses(newDoses);

    if (userId) {
      const suppStart = analyticsData?.supplement_starts?.find(
        s => s.supplement_id?.toLowerCase().replace(/-/g, '_') === supplementId
      );
      if (suppStart) {
        try {
          await api.updateSupplement(userId, suppStart.id, { dosage });
        } catch (error) {
          console.error('Error updating supplement on server:', error);
        }
      }
    }
  };

  const addSupplement = async (data: {
    supplement_id: string;
    supplement_name: string;
    dosage: string;
    timeSlot: TimeSlot;
  }) => {
    if (!userId) return;
    await api.addSupplement(userId, {
      supplement_id: data.supplement_id,
      supplement_name: data.supplement_name,
      start_date: getDateString(new Date()),
      dosage: data.dosage,
      is_manual: true,
    });
    await updateSupplementTiming(data.supplement_id, data.timeSlot);
    await refreshData();
  };

  const removeSupplement = async (supplementStartId: string) => {
    if (!userId) return;
    await api.deleteSupplement(userId, supplementStartId);
    await refreshData();
  };

  const getExistingSupplementIds = (): string[] => {
    return (analyticsData?.supplement_starts || [])
      .filter(s => !s.end_date)
      .map(s => s.supplement_id?.toLowerCase().replace(/-/g, '_'))
      .filter(Boolean) as string[];
  };

  // Life events
  const addLifeEvent = async (data: { event_type: string; event_date: string; description?: string }) => {
    if (!userId) return;
    await api.addLifeEvent(userId, data);
    await refreshData();
  };

  const deleteLifeEvent = async (eventId: string) => {
    if (!userId) return;
    await api.deleteLifeEvent(userId, eventId);
    await refreshData();
  };

  // User profile updates
  const updateUserProfile = async (updates: Partial<User>) => {
    if (!userId) return;
    const updated = await api.updateUser(userId, updates);
    setUser(updated);
  };

  // Oura management
  const disconnectOura = async () => {
    if (!userId) return;
    await api.disconnectOura(userId);
    setOuraConnected(false);
    await refreshData();
  };

  // Reset account
  const resetAccount = async () => {
    if (!userId) return;
    await api.resetAccount(userId);
    await signOut();
  };

  // Complete onboarding
  const completeOnboarding = async () => {
    if (!userId) return;
    const timestamp = new Date().toISOString();
    const updated = await api.updateUser(userId, { onboarding_complete: timestamp } as any);
    setUser(updated);
  };

  const value: AppState = useMemo(() => ({
    isLoading,
    isAuthenticated: !!user,
    user,
    userId,
    analyticsData,
    insightsData,
    selectedDate,
    ouraConnected,
    healthAlerts,
    signIn,
    signOut,
    setSelectedDate,
    refreshData,
    syncOura,
    logSupplement,
    unlogSupplement,
    updateUser: updateUserProfile,
    updateSupplementTiming,
    updateSupplementDose,
    addSupplement,
    removeSupplement,
    addLifeEvent,
    deleteLifeEvent,
    disconnectOura,
    resetAccount,
    completeOnboarding,
    getHealthDataForDate,
    getStackSupplements,
    getTodaysLogs,
    getExistingSupplementIds,
    getDateString,
  }), [
    isLoading, user, userId, analyticsData, insightsData, selectedDate,
    ouraConnected, healthAlerts, userTimings, userDoses,
  ]);

  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error('useAppState must be used within AppStateProvider');
  }
  return context;
}

// Health alert generation logic
function generateHealthAlerts(data: AnalyticsData, date: Date): HealthAlert[] {
  const alerts: HealthAlert[] = [];
  const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

  const todayData = data.health_data?.find(h => h.date === dateStr);
  if (!todayData) return alerts;

  // Calculate baselines from last 14 days
  const recentData = data.health_data
    ?.filter(h => {
      const d = new Date(h.date + 'T00:00:00');
      const diff = (date.getTime() - d.getTime()) / (1000 * 60 * 60 * 24);
      return diff > 0 && diff <= 14;
    }) || [];

  const avgScore = (key: keyof HealthData) => {
    const vals = recentData.map(d => d[key]).filter((v): v is number => v != null && typeof v === 'number');
    return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  };

  const sleepScore = todayData.sleep_score;
  const hrvScore = todayData.hrv_score;
  const recoveryScore = todayData.recovery_score;
  const tempDev = todayData.temperature_deviation;

  let lowCount = 0;

  // Immune alert - temperature deviation
  if (tempDev != null && tempDev > 0.5) {
    alerts.push({
      id: 'immune',
      type: 'immune',
      severity: tempDev > 1.0 ? 'critical' : 'warning',
      title: 'Immune System Alert',
      description: `Body temp ${tempDev > 1.0 ? 'significantly' : 'slightly'} elevated (+${tempDev.toFixed(1)}C). Your immune system may be fighting something.`,
      icon: '🛡️',
      color: '#F97316',
      actions: [
        { label: '+Vitamin C', supplementId: 'vitamin_c', type: 'add' },
        { label: '+Zinc', supplementId: 'zinc', type: 'add' },
        { label: 'Hold Caffeine', supplementId: 'caffeine', type: 'hold' },
      ],
    });
  }

  // Sleep alert
  if (sleepScore != null && sleepScore < 60) {
    lowCount++;
    alerts.push({
      id: 'sleep',
      type: 'sleep',
      severity: sleepScore < 40 ? 'critical' : 'warning',
      title: 'Sleep Recovery Support',
      description: `Sleep score ${Math.round(sleepScore)} is below optimal. Consider adjusting your evening stack.`,
      icon: '😴',
      color: '#8B5CF6',
      actions: [
        { label: '+Magnesium', supplementId: 'magnesium_glycinate', type: 'add' },
        { label: '+Apigenin', supplementId: 'apigenin', type: 'add' },
        { label: 'Limit Caffeine', supplementId: 'caffeine', type: 'reduce' },
      ],
    });
  }

  // HRV/Stress alert
  const hrvBaseline = avgScore('hrv_score');
  if (hrvScore != null && hrvBaseline != null && hrvScore < hrvBaseline * 0.75) {
    lowCount++;
    alerts.push({
      id: 'stress',
      type: 'stress',
      severity: 'warning',
      title: 'Stress Recovery Mode',
      description: `HRV is ${Math.round(((hrvBaseline - hrvScore) / hrvBaseline) * 100)}% below your baseline. Your body is under stress.`,
      icon: '🧘',
      color: '#EAB308',
      actions: [
        { label: '+Ashwagandha', supplementId: 'ashwagandha', type: 'add' },
        { label: '+L-Theanine', supplementId: 'l_theanine', type: 'add' },
        { label: 'Reduce Caffeine', supplementId: 'caffeine', type: 'reduce' },
      ],
    });
  }

  // Recovery alert
  if (recoveryScore != null && recoveryScore < 50) {
    lowCount++;
    alerts.push({
      id: 'recovery',
      type: 'recovery',
      severity: recoveryScore < 30 ? 'critical' : 'warning',
      title: 'Recovery Focus',
      description: `Recovery score ${Math.round(recoveryScore)} suggests your body needs extra support today.`,
      icon: '💪',
      color: '#22C55E',
      actions: [
        { label: '+Omega-3', supplementId: 'omega_3', type: 'add' },
        { label: '+Magnesium', supplementId: 'magnesium_glycinate', type: 'add' },
      ],
    });
  }

  // Accumulated fatigue - compound condition
  if (lowCount >= 2) {
    alerts.unshift({
      id: 'fatigue',
      type: 'fatigue',
      severity: 'critical',
      title: 'Accumulated Fatigue Detected',
      description: 'Multiple metrics are below normal. Consider a recovery day with reduced intensity.',
      icon: '⚠️',
      color: '#EF4444',
      actions: [
        { label: 'Hold Caffeine', supplementId: 'caffeine', type: 'hold' },
        { label: '+Ashwagandha', supplementId: 'ashwagandha', type: 'add' },
        { label: '+Omega-3', supplementId: 'omega_3', type: 'add' },
      ],
    });
  }

  // Only return top 2 alerts
  return alerts.slice(0, 2);
}

// DashboardScreen - Main screen with Oura metrics and supplement stack

import React, { useCallback, useState, useRef } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Linking,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  Text,
  Card,
  MetricCircle,
  DateNavigator,
  SupplementPill,
  Button,
  SupplementEditModal,
  AddSupplementModal,
  HealthAlertCard,
} from '../components';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { useAppState } from '../hooks/useAppState';
import { api } from '../services/api';
import { TimeSlot, StackSupplement, HealthAlertAction } from '../types';

export function DashboardScreen() {
  const {
    user,
    userId,
    selectedDate,
    setSelectedDate,
    ouraConnected,
    refreshData,
    syncOura,
    getHealthDataForDate,
    getStackSupplements,
    getTodaysLogs,
    logSupplement,
    unlogSupplement,
    updateSupplementTiming,
    updateSupplementDose,
    addSupplement,
    removeSupplement,
    getExistingSupplementIds,
    healthAlerts,
    isLoading,
  } = useAppState();

  const [refreshing, setRefreshing] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [selectedSupplement, setSelectedSupplement] = useState<StackSupplement | null>(null);
  // Optimistic state: track which supplements were just toggled
  const [optimisticToggles, setOptimisticToggles] = useState<Record<string, boolean>>({});
  // Lock to prevent race conditions on rapid tapping
  const inFlightRef = useRef<Record<string, boolean>>({});

  const healthData = getHealthDataForDate(selectedDate);
  const stackGroups = getStackSupplements();
  const todaysLogs = getTodaysLogs();
  const existingSupplements = getExistingSupplementIds();

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    setOptimisticToggles({}); // Clear optimistic state
    await refreshData();
    if (ouraConnected) {
      await syncOura();
    }
    setRefreshing(false);
  }, [refreshData, syncOura, ouraConnected]);

  const handleConnectOura = () => {
    if (userId) {
      const authUrl = api.getOuraAuthUrl(userId);
      Linking.openURL(authUrl);
    }
  };

  const handleSupplementPress = async (supplementId: string) => {
    if (!userId) return;

    // Prevent race condition: ignore if this supplement is already in-flight
    if (inFlightRef.current[supplementId]) return;
    inFlightRef.current[supplementId] = true;

    const log = todaysLogs[supplementId];
    const isCurrentlyTaken = !!log || optimisticToggles[supplementId] === true;

    // Optimistic update - immediately toggle the visual
    setOptimisticToggles(prev => ({
      ...prev,
      [supplementId]: !isCurrentlyTaken,
    }));

    try {
      if (log) {
        await unlogSupplement(log.id);
      } else {
        await logSupplement(supplementId);
      }
      // Clear this optimistic toggle since real data now reflects it
      setOptimisticToggles(prev => {
        const next = { ...prev };
        delete next[supplementId];
        return next;
      });
    } catch (error: any) {
      // Revert optimistic update on error
      setOptimisticToggles(prev => {
        const next = { ...prev };
        delete next[supplementId];
        return next;
      });
      Alert.alert('Error', error.message || 'Failed to log supplement');
    } finally {
      delete inFlightRef.current[supplementId];
    }
  };

  const handleSupplementLongPress = (supplement: StackSupplement) => {
    setSelectedSupplement(supplement);
    setEditModalVisible(true);
  };

  const handleEditSave = async (data: { dosage: string; timeSlot: TimeSlot }) => {
    if (!selectedSupplement) return;
    try {
      const suppId = selectedSupplement.supplement_id?.toLowerCase().replace(/-/g, '_');
      await updateSupplementDose(suppId, data.dosage);
      await updateSupplementTiming(suppId, data.timeSlot);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to save supplement changes');
    }
  };

  const handleEditDelete = async () => {
    if (!selectedSupplement) return;
    try {
      await removeSupplement(selectedSupplement.id);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to delete supplement');
    }
  };

  const handleAddSupplement = async (data: {
    supplement_id: string;
    supplement_name: string;
    dosage: string;
    timeSlot: TimeSlot;
  }) => {
    try {
      await addSupplement(data);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to add supplement');
    }
  };

  const handleAlertAction = (action: HealthAlertAction) => {
    if (action.type === 'add') {
      const name = action.supplementId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      Alert.alert(
        `Add ${name}?`,
        `Would you like to add ${name} to your supplement stack?`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Add',
            onPress: async () => {
              try {
                await addSupplement({
                  supplement_id: action.supplementId,
                  supplement_name: name,
                  dosage: '',
                  timeSlot: 'evening',
                });
              } catch (error) {
                Alert.alert('Error', 'Failed to add supplement');
              }
            },
          },
        ]
      );
    } else {
      const actionText = action.type === 'hold' ? 'hold off on' : 'reduce';
      const name = action.supplementId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      Alert.alert(
        `${action.type === 'hold' ? 'Hold' : 'Reduce'} ${name}`,
        `Consider ${actionText} ${name} based on today's metrics. You can adjust dosage from the Analytics tab.`,
        [{ text: 'Got it' }]
      );
    }
  };

  const formatSupplementName = (id: string): string => {
    return id
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  };

  // Compute isTaken considering both real logs and optimistic state
  const isTaken = (suppId: string): boolean => {
    if (suppId in optimisticToggles) {
      return optimisticToggles[suppId];
    }
    return !!todaysLogs[suppId];
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Date Navigator */}
        <DateNavigator date={selectedDate} onDateChange={setSelectedDate} />

        {/* Oura Metrics Card */}
        <Card style={styles.metricsCard}>
          <View style={styles.metricsHeader}>
            <View style={styles.ouraStatus}>
              <View style={[
                styles.statusDot,
                { backgroundColor: ouraConnected ? Colors.success : Colors.textMuted }
              ]} />
              <Text variant="caption" color="secondary">
                {ouraConnected ? 'Oura Connected' : 'Oura Not Connected'}
              </Text>
            </View>
            {ouraConnected && (
              <Text variant="caption" color="muted">
                {healthData ? 'Today\'s scores' : 'No data for this date'}
              </Text>
            )}
          </View>

          {ouraConnected ? (
            <View style={styles.metricsRow}>
              <MetricCircle
                value={healthData?.sleep_score}
                label="Sleep"
                color={Colors.sleep}
                size="md"
              />
              <MetricCircle
                value={healthData?.hrv_score}
                label="HRV"
                color={Colors.hrv}
                size="md"
              />
              <MetricCircle
                value={healthData?.recovery_score}
                label="Recovery"
                color={Colors.recovery}
                size="md"
              />
            </View>
          ) : (
            <View style={styles.connectContainer}>
              <Text variant="body" color="secondary" align="center" style={styles.connectText}>
                Connect your Oura Ring to see personalized health metrics and supplement recommendations
              </Text>
              <Button
                title="Connect Oura Ring"
                onPress={handleConnectOura}
                variant="primary"
              />
            </View>
          )}
        </Card>

        {/* Health Alerts */}
        {healthAlerts.length > 0 && (
          <View style={styles.alertsSection}>
            {healthAlerts.map(alert => (
              <HealthAlertCard
                key={alert.id}
                alert={alert}
                onActionPress={handleAlertAction}
              />
            ))}
          </View>
        )}

        {/* Your Stack Section */}
        <View style={styles.stackSection}>
          <View style={styles.stackHeader}>
            <Text variant="h3" weight="semibold">Your Stack</Text>
            <TouchableOpacity
              style={styles.addButton}
              onPress={() => setAddModalVisible(true)}
            >
              <Text style={styles.addButtonText}>+ Add</Text>
            </TouchableOpacity>
          </View>

          <Text variant="caption" color="muted" style={styles.stackHint}>
            Tap to log  •  Long press to edit
          </Text>

          {/* Morning Stack */}
          <StackTimeSection
            title="Morning"
            icon="🌅"
            supplements={stackGroups.morning}
            isTaken={isTaken}
            onSupplementPress={handleSupplementPress}
            onSupplementLongPress={handleSupplementLongPress}
            formatName={formatSupplementName}
          />

          {/* Intra-Day Stack */}
          <StackTimeSection
            title="Intra-Day"
            icon="☀️"
            supplements={stackGroups.intraday}
            isTaken={isTaken}
            onSupplementPress={handleSupplementPress}
            onSupplementLongPress={handleSupplementLongPress}
            formatName={formatSupplementName}
          />

          {/* Evening Stack */}
          <StackTimeSection
            title="Evening"
            icon="🌙"
            supplements={stackGroups.evening}
            isTaken={isTaken}
            onSupplementPress={handleSupplementPress}
            onSupplementLongPress={handleSupplementLongPress}
            formatName={formatSupplementName}
          />

          {/* Empty State */}
          {stackGroups.morning.length === 0 &&
           stackGroups.intraday.length === 0 &&
           stackGroups.evening.length === 0 && (
            <Card style={styles.emptyCard}>
              <Text variant="body" color="secondary" align="center">
                No supplements in your stack yet.
              </Text>
              <Button
                title="Add Your First Supplement"
                onPress={() => setAddModalVisible(true)}
                variant="primary"
                style={styles.emptyButton}
              />
            </Card>
          )}
        </View>
      </ScrollView>

      {/* Edit Modal */}
      <SupplementEditModal
        visible={editModalVisible}
        supplement={selectedSupplement}
        onClose={() => {
          setEditModalVisible(false);
          setSelectedSupplement(null);
        }}
        onSave={handleEditSave}
        onDelete={handleEditDelete}
      />

      {/* Add Modal */}
      <AddSupplementModal
        visible={addModalVisible}
        onClose={() => setAddModalVisible(false)}
        onAdd={handleAddSupplement}
        existingSupplements={existingSupplements}
      />
    </SafeAreaView>
  );
}

interface StackTimeSectionProps {
  title: string;
  icon: string;
  supplements: StackSupplement[];
  isTaken: (suppId: string) => boolean;
  onSupplementPress: (id: string) => void;
  onSupplementLongPress: (supplement: StackSupplement) => void;
  formatName: (id: string) => string;
}

function StackTimeSection({
  title,
  icon,
  supplements,
  isTaken,
  onSupplementPress,
  onSupplementLongPress,
  formatName,
}: StackTimeSectionProps) {
  if (supplements.length === 0) return null;

  // Count taken supplements for progress
  const takenCount = supplements.filter(s => {
    const suppId = s.supplement_id?.toLowerCase().replace(/-/g, '_');
    return isTaken(suppId);
  }).length;

  return (
    <Card style={styles.timeSection}>
      <View style={styles.timeSectionHeader}>
        <View style={styles.timeSectionLeft}>
          <Text style={styles.timeSectionIcon}>{icon}</Text>
          <Text variant="body" weight="semibold" color="secondary">
            {title}
          </Text>
        </View>
        <Text variant="caption" color="muted">
          {takenCount}/{supplements.length}
        </Text>
      </View>
      <View style={styles.pillsContainer}>
        {supplements.map((supp) => {
          const suppId = supp.supplement_id?.toLowerCase().replace(/-/g, '_');
          const name = supp.supplement_name || formatName(suppId);
          const taken = isTaken(suppId);

          return (
            <SupplementPill
              key={supp.id}
              name={name}
              dose={supp.displayDose || supp.dosage || undefined}
              isTaken={taken}
              onPress={() => onSupplementPress(suppId)}
              onLongPress={() => onSupplementLongPress(supp)}
            />
          );
        })}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: Spacing.xxxl + 40,
  },

  // Metrics Card
  metricsCard: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  metricsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  ouraStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: Spacing.md,
  },

  // Connect Oura
  connectContainer: {
    alignItems: 'center',
    paddingVertical: Spacing.lg,
    gap: Spacing.lg,
  },
  connectText: {
    paddingHorizontal: Spacing.lg,
  },

  // Health Alerts
  alertsSection: {
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.sm,
  },

  // Stack Section
  stackSection: {
    paddingHorizontal: Spacing.lg,
  },
  stackHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.xs,
  },
  stackHint: {
    marginBottom: Spacing.md,
  },
  addButton: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.primaryLight,
    borderRadius: BorderRadius.full,
  },
  addButtonText: {
    color: Colors.primary,
    fontWeight: '600',
    fontSize: 14,
  },

  // Time Section
  timeSection: {
    marginBottom: Spacing.md,
  },
  timeSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.md,
  },
  timeSectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  timeSectionIcon: {
    fontSize: 18,
  },
  pillsContainer: {
    gap: Spacing.sm,
  },

  // Empty State
  emptyCard: {
    alignItems: 'center',
    paddingVertical: Spacing.xxl,
  },
  emptyButton: {
    marginTop: Spacing.lg,
  },
});

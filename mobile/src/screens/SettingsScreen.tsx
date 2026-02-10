// SettingsScreen - User settings and account management

import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  Linking,
  Pressable,
  TextInput,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { Text, Card, Button } from '../components';
import { Colors, Spacing, BorderRadius, Typography } from '../constants/theme';
import { useAppState } from '../hooks/useAppState';
import { api } from '../services/api';
import { User } from '../types';

type EditField = 'name' | 'health_goal' | 'activity_level' | 'diet_type' | 'chronotype' | 'region' | 'age' | 'height' | 'weight' | null;

const GOAL_OPTIONS = [
  { value: 'sleep', label: 'Better Sleep' },
  { value: 'recovery', label: 'Faster Recovery' },
  { value: 'energy', label: 'More Energy' },
  { value: 'wellness', label: 'General Wellness' },
];

const ACTIVITY_OPTIONS = [
  { value: 'sedentary', label: 'Sedentary' },
  { value: 'light', label: 'Lightly Active' },
  { value: 'moderate', label: 'Moderately Active' },
  { value: 'active', label: 'Active' },
  { value: 'athlete', label: 'Athlete' },
];

const DIET_OPTIONS = [
  { value: 'omnivore', label: 'Omnivore' },
  { value: 'vegetarian', label: 'Vegetarian' },
  { value: 'vegan', label: 'Vegan' },
];

const CHRONO_OPTIONS = [
  { value: 'early_bird', label: 'Early Bird' },
  { value: 'night_owl', label: 'Night Owl' },
  { value: 'neutral', label: 'Neutral' },
];

const REGION_OPTIONS = [
  { value: 'northern', label: 'Northern US' },
  { value: 'central', label: 'Central US' },
  { value: 'southern', label: 'Southern US' },
  { value: 'gulf', label: 'Gulf Coast' },
];

export function SettingsScreen() {
  const {
    user,
    userId,
    ouraConnected,
    signOut,
    syncOura,
    updateUser,
    disconnectOura,
    resetAccount,
  } = useAppState();

  const [editField, setEditField] = useState<EditField>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const handleConnectOura = () => {
    if (userId) {
      const authUrl = api.getOuraAuthUrl(userId);
      Linking.openURL(authUrl);
    }
  };

  const handleSyncOura = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    try {
      await syncOura();
      Alert.alert('Success', 'Oura data synced successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to sync Oura data');
    }
  };

  const handleDisconnectOura = () => {
    Alert.alert(
      'Disconnect Oura',
      'This will remove your Oura Ring connection. You can reconnect anytime.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: async () => {
            try {
              await disconnectOura();
              Alert.alert('Success', 'Oura Ring disconnected');
            } catch (error) {
              Alert.alert('Error', 'Failed to disconnect Oura');
            }
          },
        },
      ]
    );
  };

  const handleSignOut = () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: signOut,
        },
      ]
    );
  };

  const handleResetAccount = () => {
    Alert.alert(
      'Reset Account',
      'This will permanently delete all your data including supplements, logs, health metrics, and life events. Your email account will be preserved.\n\nThis cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset Everything',
          style: 'destructive',
          onPress: async () => {
            try {
              await resetAccount();
            } catch (error) {
              Alert.alert('Error', 'Failed to reset account');
            }
          },
        },
      ]
    );
  };

  const openEdit = (field: EditField) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setEditField(field);
    if (field === 'name') setEditValue(user?.name || '');
    else if (field === 'age') setEditValue(user?.age?.toString() || '');
    else if (field === 'weight') setEditValue(user?.weight_lbs?.toString() || '');
  };

  const saveEdit = async (value: string) => {
    setSaving(true);
    try {
      const updates: Partial<User> = {};
      switch (editField) {
        case 'name': updates.name = value; break;
        case 'age': updates.age = parseInt(value) || undefined; break;
        case 'weight': updates.weight_lbs = parseInt(value) || undefined; break;
        case 'health_goal': updates.health_goal = value as any; break;
        case 'activity_level': updates.activity_level = value as any; break;
        case 'diet_type': updates.diet_type = value as any; break;
        case 'chronotype': updates.chronotype = value as any; break;
        case 'region': updates.region = value as any; break;
      }
      await updateUser(updates);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setEditField(null);
    } catch (error) {
      Alert.alert('Error', 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const getPickerOptions = (): { value: string; label: string }[] => {
    switch (editField) {
      case 'health_goal': return GOAL_OPTIONS;
      case 'activity_level': return ACTIVITY_OPTIONS;
      case 'diet_type': return DIET_OPTIONS;
      case 'chronotype': return CHRONO_OPTIONS;
      case 'region': return REGION_OPTIONS;
      default: return [];
    }
  };

  const isPickerField = editField && !['name', 'age', 'weight', 'height'].includes(editField);
  const currentPickerValue = () => {
    if (!user || !editField) return '';
    return (user as any)[editField] || '';
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text variant="h2" weight="bold">Settings</Text>
        </View>

        {/* User Profile Card */}
        <Card style={styles.profileCard}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <Text variant="h1" style={styles.avatarText}>
                {user?.name?.charAt(0).toUpperCase() || '?'}
              </Text>
            </View>
          </View>
          <Pressable onPress={() => openEdit('name')}>
            <Text variant="h3" weight="semibold" align="center">
              {user?.name || 'User'}
            </Text>
            <Text variant="caption" color="primary" align="center">Tap to edit</Text>
          </Pressable>
          <Text variant="bodySmall" color="secondary" align="center">
            {user?.email || ''}
          </Text>
        </Card>

        {/* Oura Integration Section */}
        <View style={styles.section}>
          <Text variant="label" color="secondary" style={styles.sectionLabel}>
            Integrations
          </Text>

          <Card style={styles.settingCard}>
            <View style={styles.settingRow}>
              <View style={styles.settingInfo}>
                <View style={styles.settingHeader}>
                  <Text variant="body" weight="medium">Oura Ring</Text>
                  <View style={[
                    styles.statusBadge,
                    { backgroundColor: ouraConnected ? Colors.successLight : Colors.backgroundElevated }
                  ]}>
                    <View style={[
                      styles.statusDot,
                      { backgroundColor: ouraConnected ? Colors.success : Colors.textMuted }
                    ]} />
                    <Text
                      variant="caption"
                      style={{ color: ouraConnected ? Colors.success : Colors.textMuted }}
                    >
                      {ouraConnected ? 'Connected' : 'Not Connected'}
                    </Text>
                  </View>
                </View>
                <Text variant="caption" color="muted">
                  {ouraConnected
                    ? 'Sleep, HRV, and recovery data synced'
                    : 'Connect to sync your health data'
                  }
                </Text>
              </View>
            </View>

            {ouraConnected ? (
              <View style={styles.ouraActions}>
                <Button
                  title="Sync Latest"
                  onPress={handleSyncOura}
                  variant="secondary"
                  size="sm"
                />
                <Button
                  title="Disconnect"
                  onPress={handleDisconnectOura}
                  variant="danger"
                  size="sm"
                />
              </View>
            ) : (
              <Button
                title="Connect Oura Ring"
                onPress={handleConnectOura}
                variant="primary"
                size="sm"
              />
            )}
          </Card>
        </View>

        {/* Profile Section - Editable */}
        {user && (
          <View style={styles.section}>
            <Text variant="label" color="secondary" style={styles.sectionLabel}>
              Profile
            </Text>

            <Card style={styles.settingCard} padding="sm">
              <EditableRow label="Health Goal" value={formatGoal(user.health_goal)} onPress={() => openEdit('health_goal')} />
              <EditableRow label="Activity Level" value={formatActivityLevel(user.activity_level)} onPress={() => openEdit('activity_level')} />
              <EditableRow label="Diet" value={formatDiet(user.diet_type)} onPress={() => openEdit('diet_type')} />
              <EditableRow label="Chronotype" value={formatChronotype(user.chronotype)} onPress={() => openEdit('chronotype')} />
              <EditableRow label="Region" value={formatRegion(user.region)} onPress={() => openEdit('region')} />
              <EditableRow label="Age" value={user.age ? `${user.age}` : 'Not set'} onPress={() => openEdit('age')} />
              <EditableRow label="Weight" value={user.weight_lbs ? `${user.weight_lbs} lbs` : 'Not set'} onPress={() => openEdit('weight')} last />
            </Card>
          </View>
        )}

        {/* About Section */}
        <View style={styles.section}>
          <Text variant="label" color="secondary" style={styles.sectionLabel}>
            About
          </Text>

          <Card style={styles.settingCard} padding="sm">
            <ProfileRow label="Version" value="1.0.0" />
            <ProfileRow label="Build" value="Expo SDK 54" last />
          </Card>
        </View>

        {/* Actions */}
        <View style={styles.actionsSection}>
          <Button
            title="Sign Out"
            onPress={handleSignOut}
            variant="danger"
            fullWidth
          />
          <Pressable onPress={handleResetAccount} style={styles.resetBtn}>
            <Text variant="caption" color="error">Reset Account Data</Text>
          </Pressable>
        </View>
      </ScrollView>

      {/* Edit Modal - Picker */}
      {isPickerField && (
        <Modal visible transparent animationType="slide">
          <Pressable style={styles.modalOverlay} onPress={() => setEditField(null)}>
            <Pressable style={styles.pickerModal}>
              <View style={styles.pickerHeader}>
                <Text variant="h3" weight="semibold">
                  {editField === 'health_goal' ? 'Health Goal' :
                   editField === 'activity_level' ? 'Activity Level' :
                   editField === 'diet_type' ? 'Diet Type' :
                   editField === 'chronotype' ? 'Chronotype' :
                   editField === 'region' ? 'Region' : ''}
                </Text>
                <Pressable onPress={() => setEditField(null)}>
                  <Text variant="body" color="primary">Done</Text>
                </Pressable>
              </View>
              <View style={styles.pickerOptions}>
                {getPickerOptions().map(opt => {
                  const isSelected = currentPickerValue() === opt.value;
                  return (
                    <Pressable
                      key={opt.value}
                      style={[styles.pickerOption, isSelected && styles.pickerOptionActive]}
                      onPress={() => saveEdit(opt.value)}
                    >
                      <Text
                        variant="body"
                        weight={isSelected ? 'semibold' : 'regular'}
                        color={isSelected ? 'primary' : 'secondary'}
                      >
                        {opt.label}
                      </Text>
                      {isSelected && <Text variant="body" color="primary">✓</Text>}
                    </Pressable>
                  );
                })}
              </View>
            </Pressable>
          </Pressable>
        </Modal>
      )}

      {/* Edit Modal - Text Input */}
      {editField && ['name', 'age', 'weight'].includes(editField) && (
        <Modal visible transparent animationType="slide">
          <Pressable style={styles.modalOverlay} onPress={() => setEditField(null)}>
            <Pressable style={styles.inputModal}>
              <View style={styles.pickerHeader}>
                <Text variant="h3" weight="semibold">
                  {editField === 'name' ? 'Your Name' :
                   editField === 'age' ? 'Your Age' :
                   'Weight (lbs)'}
                </Text>
                <Pressable onPress={() => setEditField(null)}>
                  <Text variant="body" color="muted">Cancel</Text>
                </Pressable>
              </View>
              <TextInput
                style={styles.editInput}
                value={editValue}
                onChangeText={setEditValue}
                autoFocus
                keyboardType={editField === 'name' ? 'default' : 'number-pad'}
                placeholder={editField === 'name' ? 'Enter your name' : 'Enter value'}
                placeholderTextColor={Colors.textMuted}
                maxLength={editField === 'name' ? 50 : 4}
              />
              <Button
                title={saving ? 'Saving...' : 'Save'}
                onPress={() => saveEdit(editValue)}
                variant="primary"
                fullWidth
                loading={saving}
              />
            </Pressable>
          </Pressable>
        </Modal>
      )}
    </SafeAreaView>
  );
}

function EditableRow({
  label,
  value,
  onPress,
  last = false,
}: {
  label: string;
  value: string | null | undefined;
  onPress: () => void;
  last?: boolean;
}) {
  return (
    <Pressable
      style={[styles.profileRow, !last && styles.profileRowBorder]}
      onPress={onPress}
    >
      <Text variant="bodySmall" color="secondary">{label}</Text>
      <View style={styles.editableValue}>
        <Text variant="bodySmall" weight="medium">{value || 'Not set'}</Text>
        <Text variant="caption" color="muted" style={styles.editArrow}>›</Text>
      </View>
    </Pressable>
  );
}

function ProfileRow({
  label,
  value,
  last = false,
}: {
  label: string;
  value: string | null | undefined;
  last?: boolean;
}) {
  return (
    <View style={[styles.profileRow, !last && styles.profileRowBorder]}>
      <Text variant="bodySmall" color="secondary">{label}</Text>
      <Text variant="bodySmall" weight="medium">{value || 'Not set'}</Text>
    </View>
  );
}

// Formatting helpers
function formatGoal(goal?: string | null): string {
  const map: Record<string, string> = {
    sleep: 'Better Sleep', recovery: 'Faster Recovery',
    energy: 'More Energy', wellness: 'General Wellness',
  };
  return goal ? map[goal] || goal : 'Not set';
}

function formatActivityLevel(level?: string | null): string {
  const map: Record<string, string> = {
    sedentary: 'Sedentary', light: 'Lightly Active', moderate: 'Moderately Active',
    active: 'Active', athlete: 'Athlete',
  };
  return level ? map[level] || level : 'Not set';
}

function formatDiet(diet?: string | null): string {
  const map: Record<string, string> = {
    omnivore: 'Omnivore', vegetarian: 'Vegetarian', vegan: 'Vegan',
  };
  return diet ? map[diet] || diet : 'Not set';
}

function formatChronotype(chrono?: string | null): string {
  const map: Record<string, string> = {
    early_bird: 'Early Bird', night_owl: 'Night Owl', neutral: 'Neutral',
  };
  return chrono ? map[chrono] || chrono : 'Not set';
}

function formatRegion(region?: string | null): string {
  const map: Record<string, string> = {
    northern: 'Northern US', central: 'Central US',
    southern: 'Southern US', gulf: 'Gulf Coast',
  };
  return region ? map[region] || region : 'Not set';
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

  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.lg,
  },

  // Profile Card
  profileCard: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.xl,
    alignItems: 'center',
    paddingVertical: Spacing.xl,
  },
  avatarContainer: {
    marginBottom: Spacing.md,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  avatarText: {
    color: Colors.primary,
  },

  // Section
  section: {
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.xl,
  },
  sectionLabel: {
    marginBottom: Spacing.sm,
    marginLeft: Spacing.sm,
  },
  settingCard: {
    marginBottom: Spacing.xs,
  },

  // Setting Row
  settingRow: {
    marginBottom: Spacing.md,
  },
  settingInfo: {
    flex: 1,
  },
  settingHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.full,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },

  ouraActions: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },

  // Profile Row
  profileRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.sm,
  },
  profileRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  editableValue: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  editArrow: {
    fontSize: 18,
  },

  // Actions
  actionsSection: {
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
    gap: Spacing.md,
    alignItems: 'center',
  },
  resetBtn: {
    paddingVertical: Spacing.md,
  },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: Colors.overlay,
    justifyContent: 'flex-end',
  },
  pickerModal: {
    backgroundColor: Colors.backgroundCard,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    paddingBottom: Spacing.xxxl,
  },
  inputModal: {
    backgroundColor: Colors.backgroundCard,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    paddingHorizontal: Spacing.xl,
    paddingBottom: Spacing.xxxl,
  },
  pickerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  pickerOptions: {
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing.md,
  },
  pickerOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  pickerOptionActive: {
    backgroundColor: Colors.primaryLight,
    marginHorizontal: -Spacing.md,
    paddingHorizontal: Spacing.md,
    borderRadius: BorderRadius.md,
    borderBottomWidth: 0,
  },
  editInput: {
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.lg,
    fontSize: Typography.sizes.lg,
    color: Colors.text,
    marginVertical: Spacing.xl,
  },
});

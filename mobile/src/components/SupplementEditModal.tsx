// SupplementEditModal - Modal for editing supplement details

import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text } from './Text';
import { Button } from './Button';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { TimeSlot, StackSupplement } from '../types';

interface SupplementEditModalProps {
  visible: boolean;
  supplement: StackSupplement | null;
  onClose: () => void;
  onSave: (data: { dosage: string; timeSlot: TimeSlot }) => void;
  onDelete: () => void;
}

const TIME_SLOTS: { value: TimeSlot; label: string; icon: string }[] = [
  { value: 'morning', label: 'Morning', icon: '🌅' },
  { value: 'intraday', label: 'Intra-Day', icon: '☀️' },
  { value: 'evening', label: 'Evening', icon: '🌙' },
];

const COMMON_UNITS = ['mg', 'g', 'mcg', 'IU', 'ml', 'capsules', 'tablets'];

export function SupplementEditModal({
  visible,
  supplement,
  onClose,
  onSave,
  onDelete,
}: SupplementEditModalProps) {
  const [dosage, setDosage] = useState('');
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<TimeSlot>('morning');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (supplement) {
      setDosage(supplement.displayDose || supplement.dosage || '');
      setSelectedTimeSlot(supplement.timeSlot);
      setShowDeleteConfirm(false);
    }
  }, [supplement]);

  const handleSave = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onSave({ dosage, timeSlot: selectedTimeSlot });
    onClose();
  };

  const handleDelete = () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      return;
    }
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    onDelete();
    onClose();
  };

  const handleTimeSlotChange = (slot: TimeSlot) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setSelectedTimeSlot(slot);
  };

  const handleUnitPress = (unit: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    // Extract number from current dosage
    const num = dosage.replace(/[^0-9.]/g, '');
    setDosage(num ? `${num} ${unit}` : unit);
  };

  const formatSupplementName = (id: string): string => {
    return id
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  };

  if (!supplement) return null;

  const name = supplement.supplement_name || formatSupplementName(supplement.supplement_id);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.overlay}
      >
        <Pressable style={styles.backdrop} onPress={onClose} />
        <View style={styles.content}>
          <View style={styles.handle} />

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Header */}
            <View style={styles.header}>
              <Text variant="h2" weight="bold">{name}</Text>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Text style={styles.closeIcon}>✕</Text>
              </TouchableOpacity>
            </View>

            {/* Dosage Input */}
            <View style={styles.section}>
              <Text variant="label" color="secondary" style={styles.sectionLabel}>
                Dosage
              </Text>
              <TextInput
                style={styles.input}
                value={dosage}
                onChangeText={setDosage}
                placeholder="e.g., 400 mg"
                placeholderTextColor={Colors.textMuted}
                keyboardType="default"
                autoCapitalize="none"
              />
              {/* Quick unit buttons */}
              <View style={styles.unitsRow}>
                {COMMON_UNITS.map(unit => (
                  <TouchableOpacity
                    key={unit}
                    style={[
                      styles.unitButton,
                      dosage.toLowerCase().includes(unit.toLowerCase()) && styles.unitButtonActive,
                    ]}
                    onPress={() => handleUnitPress(unit)}
                  >
                    <Text
                      variant="caption"
                      color={dosage.toLowerCase().includes(unit.toLowerCase()) ? 'primary' : 'secondary'}
                      weight={dosage.toLowerCase().includes(unit.toLowerCase()) ? 'semibold' : 'regular'}
                    >
                      {unit}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Time Slot Selection */}
            <View style={styles.section}>
              <Text variant="label" color="secondary" style={styles.sectionLabel}>
                Time of Day
              </Text>
              <View style={styles.timeSlotsRow}>
                {TIME_SLOTS.map(slot => (
                  <TouchableOpacity
                    key={slot.value}
                    style={[
                      styles.timeSlotButton,
                      selectedTimeSlot === slot.value && styles.timeSlotButtonActive,
                    ]}
                    onPress={() => handleTimeSlotChange(slot.value)}
                  >
                    <Text style={styles.timeSlotIcon}>{slot.icon}</Text>
                    <Text
                      variant="bodySmall"
                      weight={selectedTimeSlot === slot.value ? 'semibold' : 'regular'}
                      color={selectedTimeSlot === slot.value ? 'primary' : 'secondary'}
                    >
                      {slot.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Save Button */}
            <Button
              title="Save Changes"
              onPress={handleSave}
              variant="primary"
              fullWidth
              style={styles.saveButton}
            />

            {/* Delete Section */}
            <TouchableOpacity
              style={[styles.deleteButton, showDeleteConfirm && styles.deleteButtonConfirm]}
              onPress={handleDelete}
            >
              <Text
                variant="body"
                weight="medium"
                color={showDeleteConfirm ? 'error' : 'muted'}
              >
                {showDeleteConfirm ? 'Tap again to confirm delete' : 'Remove from stack'}
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  content: {
    backgroundColor: Colors.backgroundElevated,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.xxxl,
    maxHeight: '80%',
  },
  handle: {
    width: 36,
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.xl,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeIcon: {
    fontSize: 16,
    color: Colors.textMuted,
  },
  section: {
    marginBottom: Spacing.xl,
  },
  sectionLabel: {
    marginBottom: Spacing.sm,
  },
  input: {
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: 16,
    color: Colors.text,
  },
  unitsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
    marginTop: Spacing.sm,
  },
  unitButton: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  unitButtonActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  timeSlotsRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  timeSlotButton: {
    flex: 1,
    flexDirection: 'column',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.xs,
  },
  timeSlotButtonActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  timeSlotIcon: {
    fontSize: 24,
  },
  saveButton: {
    marginBottom: Spacing.lg,
  },
  deleteButton: {
    alignItems: 'center',
    paddingVertical: Spacing.md,
  },
  deleteButtonConfirm: {
    backgroundColor: Colors.errorLight,
    borderRadius: BorderRadius.md,
  },
});
